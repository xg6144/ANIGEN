import json
import os
import re
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

import requests
import torch
from PIL import Image
from diffusers import Flux2KleinPipeline
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field


MODEL_NAME = "google/gemma-4-26B-A4B-it"
LLM_BASE_URL = "<LLM Server URL>/v1"
SCENE_COUNT = 6
CHARACTER_OPTION_COUNT = 3
CHARACTER_IMAGE_DEVICE = "cuda:2"
SCENE_IMAGE_DEVICE = "cuda:3"
FLUX_IMAGE_MODEL_CACHE_DIR = Path("/ssd4/dongbeen/hf_models/models--black-forest-labs--FLUX.2-klein-9b-kv")
GENERATED_DIR = Path(__file__).resolve().parent / "generated"
VIDEO_SERVICE_BASE_URL = os.getenv("MAGIHUMAN_API_BASE_URL", "http://127.0.0.1:8899").rstrip("/")
VIDEO_SERVICE_TIMEOUT_SECONDS = int(os.getenv("MAGIHUMAN_API_TIMEOUT_SECONDS", "3600"))
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
IMAGE_HEIGHT = 1024
IMAGE_WIDTH = 1024
CHARACTER_IMAGE_INFERENCE_STEPS = 4
SCENE_IMAGE_INFERENCE_STEPS = 4
LLM_TEMPERATURE = 0.2
LLM_TOP_P = 0.9
LLM_TOP_K = 20
LLM_PRESENCE_PENALTY = 0.0
LLM_REPETITION_PENALTY = 1.0
ANIMATION_STYLE_PREFIX = (
    "Japanese anime protagonist style, anime key visual, stylized 2d character design, "
    "clean line art, cel shading, expressive eyes, polished hair rendering, "
    "heroic silhouette, single character, full body, family-friendly, minimal studio background"
)

client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key="EMPTY",
    timeout=3600,
)
character_image_generation_lock = Lock()
scene_image_generation_lock = Lock()


class StoryboardRequest(BaseModel):
    character: str = Field(min_length=1, max_length=200)
    background: str = Field(min_length=1, max_length=200)
    event: str = Field(min_length=1, max_length=400)


class StoryboardScene(BaseModel):
    title: str
    summary: str
    visual: str


class StoryboardResponse(BaseModel):
    title: str
    synopsis: str
    scenes: list[StoryboardScene]


class CharacterDesignRequest(BaseModel):
    character: str = Field(min_length=1, max_length=200)
    background: str = Field(min_length=1, max_length=200)
    event: str = Field(min_length=1, max_length=400)
    storyboard: StoryboardResponse


class CharacterImageRequest(BaseModel):
    character: str = Field(min_length=1, max_length=200)
    advanced_prompt: str = Field(default="", max_length=600)
    render_dimension: Literal["2d", "3d", "real-person"]
    style: Literal["pixar", "anime"] | None = None


class CharacterImageResponse(BaseModel):
    image_url: str
    prompt: str
    summary: str
    render_dimension: str
    style: str | None


class CharacterPromptOption(BaseModel):
    label: str
    summary: str
    prompt: str


class CharacterPromptResponse(BaseModel):
    character_summary: str
    options: list[CharacterPromptOption]


class ReferenceCharacterImage(BaseModel):
    label: str
    summary: str
    prompt: str
    image_url: str
    render_dimension: str | None = None
    style: str | None = None


class CharacterDesignOption(ReferenceCharacterImage):
    option_id: str


class CharacterDesignResponse(BaseModel):
    character_summary: str
    options: list[CharacterDesignOption]


class SceneImageRequest(BaseModel):
    character: str = Field(min_length=1, max_length=200)
    background: str = Field(min_length=1, max_length=200)
    event: str = Field(min_length=1, max_length=400)
    storyboard: StoryboardResponse
    selected_character: ReferenceCharacterImage
    scene_indices: list[int] | None = None


class SceneImagePromptScene(BaseModel):
    scene_index: int
    prompt: str


class SceneImagePromptResponse(BaseModel):
    scenes: list[SceneImagePromptScene]


class SceneImageOption(BaseModel):
    scene_index: int
    title: str
    summary: str
    visual: str
    image_url: str


class SceneImageResponse(BaseModel):
    scenes: list[SceneImageOption]


class FinalVideoRequest(BaseModel):
    character: str = Field(min_length=1, max_length=200)
    background: str = Field(min_length=1, max_length=200)
    event: str = Field(min_length=1, max_length=400)
    storyboard: StoryboardResponse
    selected_character: ReferenceCharacterImage
    scenes: list[SceneImageOption]
    seconds_per_scene: int = Field(default=10, ge=1, le=10)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class SceneVideoPromptScene(BaseModel):
    scene_index: int
    scene_description: str = Field(min_length=1)
    dialogue_line: str = Field(min_length=1)
    background_sound_line: str = Field(min_length=1)


class SceneVideoPromptResponse(BaseModel):
    scenes: list[SceneVideoPromptScene]


class FinalVideoScene(BaseModel):
    scene_index: int
    title: str
    summary: str
    image_url: str
    video_url: str


class FinalVideoResponse(BaseModel):
    video_url: str
    scenes: list[FinalVideoScene]


def resolve_model_snapshot_path(model_cache_dir: Path, model_label: str) -> Path:
    if not model_cache_dir.exists():
        raise RuntimeError(f"{model_label} snapshot was not found in /ssd4/dongbeen/hf_models")

    ref_path = model_cache_dir / "refs" / "main"
    if ref_path.exists():
        revision = ref_path.read_text(encoding="utf-8").strip()
        candidate = model_cache_dir / "snapshots" / revision
        if (candidate / "model_index.json").exists():
            return candidate

    snapshot_dir = model_cache_dir / "snapshots"
    for candidate in sorted(snapshot_dir.iterdir(), reverse=True):
        if (candidate / "model_index.json").exists():
            return candidate

    raise RuntimeError(f"{model_label} snapshot was not found in /ssd4/dongbeen/hf_models")


def ensure_cuda_device(device: str, model_label: str) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError(f"CUDA is required to load {model_label}")

    if not device.startswith("cuda:"):
        raise RuntimeError(f"Unsupported CUDA device format for {model_label}: {device}")

    device_index = int(device.split(":", maxsplit=1)[1])
    available_device_count = torch.cuda.device_count()
    if device_index >= available_device_count:
        raise RuntimeError(
            f"{model_label} requires GPU {device_index}, but only {available_device_count} CUDA device(s) are available"
        )


def load_flux2_klein_pipeline(device: str) -> Flux2KleinPipeline:
    ensure_cuda_device(device, "FLUX.2-klein-9b-kv")
    snapshot_path = resolve_model_snapshot_path(
        FLUX_IMAGE_MODEL_CACHE_DIR,
        "FLUX.2-klein-9b-kv",
    )
    pipe = Flux2KleinPipeline.from_pretrained(
        str(snapshot_path),
        torch_dtype=torch.bfloat16,
        local_files_only=True,
    )
    pipe.to(device)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def load_image_pipeline() -> Flux2KleinPipeline:
    return load_flux2_klein_pipeline(CHARACTER_IMAGE_DEVICE)


def load_scene_image_pipeline() -> Flux2KleinPipeline:
    return load_flux2_klein_pipeline(SCENE_IMAGE_DEVICE)


def get_scene_image_pipeline(app: FastAPI):
    pipe = getattr(app.state, "scene_image_pipe", None)
    if pipe is None:
        raise RuntimeError("Scene image pipeline is not loaded")
    return pipe


@asynccontextmanager
async def lifespan(app: FastAPI):
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    app.state.character_image_pipe = load_image_pipeline()
    app.state.scene_image_pipe = load_scene_image_pipeline()
    yield
    character_image_pipe = getattr(app.state, "character_image_pipe", None)
    if character_image_pipe is not None:
        del character_image_pipe
    scene_image_pipe = getattr(app.state, "scene_image_pipe", None)
    if scene_image_pipe is not None:
        del scene_image_pipe
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(title="ANIGEN Storyboard API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated", StaticFiles(directory=GENERATED_DIR, check_dir=False), name="generated")


def build_storyboard_prompt(payload: StoryboardRequest) -> str:
    return f"""
너는 애니메이션 스토리보드 작가다.
아래 입력을 바탕으로 짧고 선명한 {SCENE_COUNT}컷 스토리보드를 한국어로 작성해라.

입력값
- 주인공: {payload.character}
- 배경: {payload.background}
- 사건: {payload.event}

반드시 아래 JSON만 출력해라. 마크다운, 설명, 코드블록은 금지한다.
각 scene은 장면 제목, 2~3문장 요약, 이미지 생성에 쓸 수 있는 시각 묘사를 포함해야 한다.
scene은 반드시 총 {SCENE_COUNT}개여야 한다.
주인공의 외형은 직접 확정하지 말고, 이야기 톤과 역할에 맞는 시각 단서를 자연스럽게 반복해라.
모든 scene에서 같은 주인공으로 인식될 수 있게 헤어스타일, 복장 분위기, 실루엣 같은 단서를 일관되게 유지해라.

{{
  "title": "스토리 제목",
  "synopsis": "이야기 전체를 한두 문장으로 요약",
  "scenes": [
    {{
      "title": "장면 1 제목",
      "summary": "장면 설명",
      "visual": "시각 묘사"
    }},
    {{
      "title": "장면 2 제목",
      "summary": "장면 설명",
      "visual": "시각 묘사"
    }},
    {{
      "title": "장면 3 제목",
      "summary": "장면 설명",
      "visual": "시각 묘사"
    }},
    {{
      "title": "장면 4 제목",
      "summary": "장면 설명",
      "visual": "시각 묘사"
    }},
    {{
      "title": "장면 5 제목",
      "summary": "장면 설명",
      "visual": "시각 묘사"
    }},
    {{
      "title": "장면 6 제목",
      "summary": "장면 설명",
      "visual": "시각 묘사"
    }}
  ]
}}
""".strip()


def build_character_prompt(payload: CharacterDesignRequest) -> str:
    scenes_text = "\n".join(
        f"- {index + 1}. {scene.title}: {scene.summary} / {scene.visual}"
        for index, scene in enumerate(payload.storyboard.scenes)
    )

    return f"""
너는 일본 애니메이션 주인공 캐릭터를 설계하는 컨셉 아티스트다.
아래 스토리보드를 분석해서 동일한 주인공의 외형 시안 3개를 설계해라.

요구사항
- 출력은 반드시 JSON만 사용한다.
- 설명, 코드블록, 마크다운은 금지한다.
- options는 정확히 3개여야 한다.
- prompt는 영어로 작성한다.
- 각 prompt는 단일 캐릭터만 나오게 한다.
- 각 prompt는 반드시 일본 애니메이션 주인공 스타일의 2D 캐릭터 컨셉 아트로 작성한다.
- photorealistic, live action, cinematic photo, realistic skin, 3d render 표현은 금지한다.
- Japanese anime protagonist, anime hero design, clean line art, cel shading, stylized 2D illustration 의미가 분명히 드러나야 한다.
- 전신 기준의 캐릭터 컨셉 아트 스타일로 작성한다.
- 배경은 단순한 스튜디오 또는 부드러운 그라데이션으로 최소화한다.
- 전연령용, 비선정적, 비폭력적으로 작성한다.
- 스토리 정보에서 주인공의 성격, 역할, 세계관에 어울리는 외형을 추론해라.
- 장면별 상황을 따로 그림으로 만들지 말고, 한 명의 주인공 외형 설계에 집중해라.
- 3개 시안은 같은 이야기의 주인공 후보여야 하며, 헤어스타일, 의상 레이어, 색 조합, 액세서리 방향성을 다르게 제안해라.
- 각 시안은 포즈, 표정, 손동작, 소품에서 차이를 줄 수 있지만, 가장 중요한 차이는 외형 디자인 방향이어야 한다.
- 특정 기존 애니메이션 캐릭터 이름이나 작품명을 직접 언급하지 마라.

입력값
- 주인공: {payload.character}
- 배경: {payload.background}
- 사건: {payload.event}
- 스토리 제목: {payload.storyboard.title}
- 스토리 요약: {payload.storyboard.synopsis}
- 장면 요약:
{scenes_text}

반드시 아래 형식만 출력해라.
{{
  "character_summary": "스토리보드에서 추론한 주인공 외형 방향을 한국어로 1~2문장 요약",
  "options": [
    {{
      "label": "시안 1",
      "summary": "시안 특징을 한국어 한 문장으로 설명",
      "prompt": "English prompt"
    }},
    {{
      "label": "시안 2",
      "summary": "시안 특징을 한국어 한 문장으로 설명",
      "prompt": "English prompt"
    }},
    {{
      "label": "시안 3",
      "summary": "시안 특징을 한국어 한 문장으로 설명",
      "prompt": "English prompt"
    }}
  ]
}}
""".strip()


def get_requested_storyboard_scenes(
    storyboard: StoryboardResponse,
    scene_indices: list[int] | None = None,
) -> list[tuple[int, StoryboardScene]]:
    if scene_indices is None:
        return [
            (index + 1, scene)
            for index, scene in enumerate(storyboard.scenes)
        ]

    if not scene_indices:
        raise ValueError("scene_indices must not be empty")

    seen_indices: set[int] = set()
    requested_scenes: list[tuple[int, StoryboardScene]] = []
    total_scene_count = len(storyboard.scenes)

    for scene_index in scene_indices:
        if scene_index in seen_indices:
            raise ValueError("scene_indices must not contain duplicates")
        if scene_index < 1 or scene_index > total_scene_count:
            raise ValueError(f"scene_index must be between 1 and {total_scene_count}")

        seen_indices.add(scene_index)
        requested_scenes.append((scene_index, storyboard.scenes[scene_index - 1]))

    requested_scenes.sort(key=lambda item: item[0])
    return requested_scenes


def build_scene_image_prompt(payload: SceneImageRequest) -> str:
    requested_scenes = get_requested_storyboard_scenes(
        payload.storyboard,
        payload.scene_indices,
    )
    render_dimension = payload.selected_character.render_dimension or "2d"
    style = payload.selected_character.style or "anime"
    if render_dimension == "real-person":
        prompt_role = "image-to-image realistic cinematic scene prompt designer"
        scene_style_line = (
            "- 각 prompt는 realistic cinematic scene, natural lighting, believable materials, "
            "lifelike human presence가 분명해야 한다."
        )
        negative_style_line = (
            "- anime, cartoon, cel shading, stylized 2d illustration, exaggerated toon features, "
            "chibi, text, watermark 표현은 금지한다."
        )
        character_consistency_line = (
            "- 각 prompt는 반드시 참조 주인공 이미지의 실제 얼굴 구조, 피부 질감, 헤어스타일, "
            "의상 디테일을 유지해야 한다."
        )
    elif render_dimension == "3d":
        prompt_role = "image-to-image stylized 3d animated scene prompt designer"
        scene_style_line = (
            "- 각 prompt는 polished stylized 3d animated scene, dimensional character rendering, "
            "cinematic lighting이 분명해야 한다."
        )
        negative_style_line = (
            "- photorealistic live action, realistic skin pores, flat 2d illustration, text, watermark 표현은 금지한다."
        )
        character_consistency_line = (
            "- 각 prompt는 반드시 참조 주인공 이미지의 얼굴, 헤어스타일, 색 조합, 핵심 의상 디테일을 유지해야 한다."
        )
    else:
        prompt_role = "image-to-image animated scene prompt designer"
        scene_style_line = (
            "- 각 prompt는 Japanese anime inspired theatrical scene, stylized illustration, "
            "clean shapes, expressive staging이 분명해야 한다."
        )
        negative_style_line = (
            "- photorealistic, live action, realistic skin, 3d render, text, watermark 표현은 금지한다."
        )
        character_consistency_line = (
            "- 각 prompt는 반드시 참조 주인공 이미지의 얼굴, 헤어스타일, 색 조합, 핵심 의상 디테일을 유지해야 한다."
        )

    scenes_text = "\n".join(
        f"- {scene_index}. {scene.title}: {scene.summary} / {scene.visual}"
        for scene_index, scene in requested_scenes
    )
    scene_schema = ",\n".join(
        f"""    {{
      "scene_index": {scene_index},
      "prompt": "English prompt"
    }}"""
        for scene_index, _scene in requested_scenes
    )

    return f"""
너는 {prompt_role}다.
참조 주인공 이미지를 사용해서 각 장면용 영문 프롬프트를 작성해라.

요구사항
- 출력은 반드시 JSON만 사용한다.
- 설명, 코드블록, 마크다운은 금지한다.
- scenes는 정확히 {len(requested_scenes)}개여야 한다.
- prompt는 영어로 작성한다.
- 참조 캐릭터 형식: {render_dimension}
- 참조 캐릭터 스타일: {style}
{character_consistency_line}
{scene_style_line}
- 각 prompt는 provided reference character image를 기반으로 같은 캐릭터를 유지하라는 의미가 드러나야 한다.
- 장면 요약과 시각 묘사를 반영해 배경, 행동, 구도, 조명, 감정을 구체화해라.
- 필요하면 소품이나 배경 인물을 넣을 수 있지만, 주인공이 장면의 중심으로 읽혀야 한다.
{negative_style_line}
- 특정 기존 애니메이션 캐릭터명이나 작품명은 직접 언급하지 마라.

입력값
- 주인공: {payload.character}
- 배경: {payload.background}
- 사건: {payload.event}
- 스토리 제목: {payload.storyboard.title}
- 스토리 요약: {payload.storyboard.synopsis}
- 참조 이미지 이름: {payload.selected_character.label}
- 참조 이미지 요약: {payload.selected_character.summary}
- 참조 이미지 원본 프롬프트: {payload.selected_character.prompt}
- 장면 요약:
{scenes_text}

반드시 아래 형식만 출력해라.
{{
  "scenes": [
{scene_schema}
  ]
}}
""".strip()


def build_scene_video_prompt(payload: FinalVideoRequest) -> str:
    render_dimension = payload.selected_character.render_dimension or "2d"
    style = payload.selected_character.style or "anime"
    if render_dimension == "real-person":
        prompt_role = "realistic image-based video prompt designer"
        motion_style_line = (
            "- 각 prompt는 realistic human motion, natural facial movement, grounded camera behavior, believable lighting을 반영해야 한다."
        )
        negative_style_line = (
            "- anime motion, cartoon exaggeration, cel shading, stylized 2d illustration, text, watermark 표현은 금지한다."
        )
        medium_line = "- 영상은 사실적인 실사풍 장면처럼 보여야 하며, 과장된 애니메이션 움직임은 금지한다."
    elif render_dimension == "3d":
        prompt_role = "stylized 3d image-based video prompt designer"
        motion_style_line = (
            "- 각 prompt는 polished 3d animated motion, dimensional lighting, expressive but coherent performance를 반영해야 한다."
        )
        negative_style_line = (
            "- photorealistic live action, realistic skin pores, flat 2d illustration, text, watermark 표현은 금지한다."
        )
        medium_line = "- 영상은 부드러운 3D 애니메이션 장면처럼 보여야 하며, 갑작스러운 장면 전환이나 컷 분할은 금지한다."
    else:
        prompt_role = "animated image-based video prompt designer"
        motion_style_line = (
            "- 각 prompt는 anime-style motion, stylized acting, cinematic illustrated scene continuity를 반영해야 한다."
        )
        negative_style_line = (
            "- photorealistic, live action, realistic skin, 3d render, text, watermark 표현은 금지한다."
        )
        medium_line = "- 영상은 부드러운 애니메이션 장면처럼 보여야 하며, 갑작스러운 장면 전환이나 컷 분할은 금지한다."

    scenes_text = "\n".join(
        f"- {scene.scene_index}. {scene.title}: {scene.summary} / {scene.visual}"
        for scene in payload.scenes
    )
    scene_schema = ",\n".join(
        f"""    {{
      "scene_index": {scene.scene_index},
      "scene_description": "English motion and camera direction paragraph",
      "dialogue_line": "Dialogue: <Main character, Korean>: \\"한국어 대사\\"",
      "background_sound_line": "Background Sound: <No prominent background sound>"
    }}"""
        for scene in payload.scenes
    )

    return f"""
너는 {prompt_role}다.
이미 생성된 장면 이미지를 바탕으로 각 장면을 짧은 영상으로 만들기 위한 영문 프롬프트를 작성해라.

요구사항
- 출력은 반드시 JSON만 사용한다.
- 설명, 코드블록, 마크다운은 금지한다.
- scenes는 정확히 {len(payload.scenes)}개여야 한다.
- 참조 캐릭터 형식: {render_dimension}
- 참조 캐릭터 스타일: {style}
- 각 scene_description은 영어로 작성한 한 문단이어야 한다.
- 각 scene_description은 생성된 장면 이미지의 캐릭터 외형, 의상, 색 조합, 배경 구성을 유지해야 한다.
- 각 scene_description은 약 {payload.seconds_per_scene}초 분량의 단일 샷을 가정하고, 미세한 동작, 표정 변화, 카메라 프레이밍, 분위기, 조명을 구체적으로 적어라.
- {motion_style_line.removeprefix("- ")}
- 각 dialogue_line은 반드시 한 줄로 작성하고 정확히 `Dialogue: <speaker description in English, Korean>: "한국어 대사"` 형식을 사용해라.
- 각 dialogue_line의 따옴표 안 실제 대사는 반드시 한국어만 사용해라. 영어 번역, 로마자 표기, `No dialogue`는 금지한다.
- 각 scene마다 대사를 반드시 하나씩 생성해라. 장면의 감정과 사건 진행에 맞는 짧고 자연스러운 한국어 한 문장으로 작성해라.
- 각 background_sound_line은 반드시 한 줄로 작성하고 정확히 `Background Sound: <...>` 형식을 사용해라.
- 배경음 묘사는 영어로 작성해라.
- 배경음이 거의 없으면 `Background Sound: <No prominent background sound>`를 사용해라.
- scene_description 안에 `Dialogue:` 또는 `Background Sound:`를 넣지 마라.
- {medium_line.removeprefix("- ")}
- {negative_style_line.removeprefix("- ")}
- 특정 기존 애니메이션 캐릭터 이름이나 작품명은 직접 언급하지 마라.

입력값
- 주인공: {payload.character}
- 배경: {payload.background}
- 사건: {payload.event}
- 스토리 제목: {payload.storyboard.title}
- 스토리 요약: {payload.storyboard.synopsis}
- 선택한 시안 이름: {payload.selected_character.label}
- 선택한 시안 요약: {payload.selected_character.summary}
- 선택한 시안 원본 프롬프트: {payload.selected_character.prompt}
- 장면 목록:
{scenes_text}

반드시 아래 형식만 출력해라.
{{
  "scenes": [
{scene_schema}
  ]
}}
""".strip()


def extract_json_object(content: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(content):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(content[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError("LLM response did not contain valid JSON")


def request_llm_json(prompt: str, max_tokens: int) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=max_tokens,
        temperature=LLM_TEMPERATURE,
        top_p=LLM_TOP_P,
        presence_penalty=LLM_PRESENCE_PENALTY,
        extra_body={
            "top_k": LLM_TOP_K,
            "repetition_penalty": LLM_REPETITION_PENALTY,
            "enable_thinking": False,
        },
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("LLM returned empty content")

    return extract_json_object(content)


def build_generated_asset_url(file_path: Path) -> str:
    relative_path = file_path.resolve().relative_to(GENERATED_DIR.resolve())
    return f"/generated/{relative_path.as_posix()}"


def save_generated_image(image, option_id: str) -> str:
    file_path = GENERATED_DIR / f"{option_id}.png"
    image.save(file_path)
    return build_generated_asset_url(file_path)


def compose_character_image_prompt(prompt: str) -> str:
    normalized_prompt = " ".join(prompt.split())
    return f"{ANIMATION_STYLE_PREFIX}, {normalized_prompt}"


def compose_single_character_image_prompt(payload: CharacterImageRequest) -> str:
    prompt_parts = [
        f"main character concept based on {payload.character}",
        "single character",
        "full body",
        "centered composition",
        "plain studio backdrop",
        "family-friendly",
        "high detail",
        "no text",
        "no watermark",
    ]

    if payload.render_dimension == "2d":
        prompt_parts.extend(
            [
                "stylized 2d character illustration",
                "clean line art",
                "refined shading",
                "concept art presentation",
            ]
        )
    elif payload.render_dimension == "3d":
        prompt_parts.extend(
            [
                "stylized 3d character render",
                "dimensional modeling",
                "polished surface detail",
                "soft cinematic lighting",
            ]
        )
    else:
        prompt_parts.extend(
            [
                "real human portrait",
                "photorealistic facial details",
                "natural skin texture",
                "real-world clothing",
                "studio photography lighting",
            ]
        )

    if payload.render_dimension == "real-person":
        pass
    elif payload.style == "pixar":
        prompt_parts.extend(
            [
                "warm family animation feature aesthetic",
                "appealing character shapes",
                "expressive face",
                "playful charm",
            ]
        )
    elif payload.style == "anime":
        prompt_parts.extend(
            [
                "Japanese anime inspired character design",
                "expressive eyes",
                "distinct silhouette",
                "vibrant color styling",
            ]
        )
    elif payload.style is None:
        raise ValueError("style is required for 2d or 3d character generation")

    if payload.advanced_prompt.strip():
        prompt_parts.append(payload.advanced_prompt.strip())

    return ", ".join(" ".join(prompt_parts).split())


def build_single_character_summary(payload: CharacterImageRequest) -> str:
    render_dimension_label = {
        "2d": "2D 캐릭터",
        "3d": "3D 캐릭터",
        "real-person": "현실 사람",
    }[payload.render_dimension]
    style_label = {
        "pixar": "픽사 애니메이션풍",
        "anime": "일본 애니메이션풍",
    }.get(payload.style)
    if style_label is None:
        return f"{payload.character} 주인공을 {render_dimension_label} 방향으로 생성한 이미지입니다."
    return f"{payload.character} 주인공을 {render_dimension_label}, {style_label} 방향으로 생성한 이미지입니다."


def resolve_generated_asset_path(asset_url: str) -> Path:
    generated_prefix = "/generated/"
    if not asset_url.startswith(generated_prefix):
        raise ValueError("Generated asset must be served from /generated")

    relative_path = asset_url.removeprefix(generated_prefix).lstrip("/")
    resolved_path = (GENERATED_DIR / relative_path).resolve()
    generated_root = GENERATED_DIR.resolve()
    if resolved_path != generated_root and generated_root not in resolved_path.parents:
        raise ValueError("Generated asset path is invalid")
    if not resolved_path.exists() or not resolved_path.is_file():
        raise FileNotFoundError(f"Generated asset was not found: {relative_path}")

    return resolved_path


def order_scene_prompts(
    prompt_response: SceneImagePromptResponse | SceneVideoPromptResponse,
    expected_indices: list[int],
) -> list[SceneImagePromptScene] | list[SceneVideoPromptScene]:
    if len(prompt_response.scenes) != len(expected_indices):
        raise ValueError(f"Scene prompt response must contain exactly {len(expected_indices)} scenes")

    scene_prompt_map = {scene.scene_index: scene for scene in prompt_response.scenes}
    if sorted(scene_prompt_map) != expected_indices:
        raise ValueError("Scene prompt response must include every scene_index exactly once")

    return [scene_prompt_map[index] for index in expected_indices]


def order_scene_images(
    scenes: list[SceneImageOption],
    expected_count: int,
) -> list[SceneImageOption]:
    if len(scenes) != expected_count:
        raise ValueError(f"Scene image response must contain exactly {expected_count} scenes")

    scene_map = {scene.scene_index: scene for scene in scenes}
    expected_indices = list(range(1, expected_count + 1))
    if sorted(scene_map) != expected_indices:
        raise ValueError("Scene image response must include every scene_index exactly once")

    return [scene_map[index] for index in expected_indices]


def contains_korean_text(value: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in value)


def normalize_prompt_line(value: str) -> str:
    return " ".join(part.strip() for part in value.splitlines() if part.strip())


def normalize_scene_description(value: str) -> str:
    cleaned_lines = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^(dialogue|dialog|대사|background sound|background|sound|배경음)\s*:", line, flags=re.IGNORECASE):
            continue
        cleaned_lines.append(line)

    normalized = " ".join(cleaned_lines)
    if not normalized:
        raise ValueError("Scene video description must not be empty")
    return normalized


def normalize_dialogue_line(value: str) -> str:
    line = normalize_prompt_line(value)
    if not line:
        raise ValueError("Scene video prompt dialogue must not be empty")

    line = re.sub(r"^(dialogue|dialog|대사)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
    if "<No dialogue>" in line or line.lower() == "no dialogue":
        raise ValueError("Scene video prompt dialogue must be generated for every scene")

    speaker_match = re.search(r"<([^>]+)>", line)
    speaker = speaker_match.group(1).strip() if speaker_match else "Main character, Korean"
    if "korean" not in speaker.lower():
        speaker = f"{speaker}, Korean"

    quoted_match = re.search(r'["“](.+?)["”]', line)
    if quoted_match:
        dialogue_text = quoted_match.group(1).strip()
    else:
        dialogue_text = re.sub(r"<[^>]+>\s*:?\s*", "", line).strip()
        dialogue_text = dialogue_text.strip(' "\'“”')

    if not dialogue_text or not contains_korean_text(dialogue_text):
        raise ValueError("Scene video prompt dialogue must include Korean text")

    return f'Dialogue: <{speaker}>: "{dialogue_text}"'


def normalize_background_sound_line(value: str) -> str:
    line = normalize_prompt_line(value)
    line = re.sub(
        r"^(background sound|background|sound|bgm|배경음|배경음향)\s*:\s*",
        "",
        line,
        flags=re.IGNORECASE,
    ).strip()

    if not line:
        content = "No prominent background sound"
    else:
        angle_match = re.search(r"<([^>]+)>", line)
        content = angle_match.group(1).strip() if angle_match else line.strip("<>").strip()
        if not content:
            content = "No prominent background sound"

    return f"Background Sound: <{content}>"


def normalize_scene_video_prompts(scene_prompts: list[SceneVideoPromptScene]) -> list[SceneVideoPromptScene]:
    normalized_prompts: list[SceneVideoPromptScene] = []
    for scene_prompt in scene_prompts:
        normalized_prompts.append(
            scene_prompt.model_copy(
                update={
                    "scene_description": normalize_scene_description(scene_prompt.scene_description),
                    "dialogue_line": normalize_dialogue_line(scene_prompt.dialogue_line),
                    "background_sound_line": normalize_background_sound_line(scene_prompt.background_sound_line),
                }
            )
        )
    return normalized_prompts


def validate_scene_video_prompts(scene_prompts: list[SceneVideoPromptScene]) -> None:
    for scene_prompt in scene_prompts:
        if "Dialogue:" in scene_prompt.scene_description or "Background Sound:" in scene_prompt.scene_description:
            raise ValueError("Scene video description must not include Dialogue or Background Sound lines")
        if not scene_prompt.dialogue_line.startswith("Dialogue: <"):
            raise ValueError("Scene video prompt dialogue_line must start with 'Dialogue: <'")
        if "<No dialogue>" in scene_prompt.dialogue_line:
            raise ValueError("Scene video prompt dialogue must be generated for every scene")
        if not contains_korean_text(scene_prompt.dialogue_line):
            raise ValueError("Scene video prompt dialogue must include Korean text")
        if not scene_prompt.background_sound_line.startswith("Background Sound: <"):
            raise ValueError("Scene video prompt background_sound_line must start with 'Background Sound: <'")


def compose_scene_video_generation_prompt(scene_prompt: SceneVideoPromptScene) -> str:
    scene_description = normalize_prompt_line(scene_prompt.scene_description)
    dialogue_line = normalize_prompt_line(scene_prompt.dialogue_line)
    background_sound_line = normalize_prompt_line(scene_prompt.background_sound_line)
    return f"{scene_description}\n\n{dialogue_line}\n{background_sound_line}"


def extract_video_service_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("error")
            if detail:
                return str(detail)
    except ValueError:
        pass

    return response.text.strip() or f"HTTP {response.status_code}"


def guess_upload_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def generate_scene_video_file(
    prompt: str,
    image_path: Path,
    output_path: Path,
    *,
    seconds: int,
    seed: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request_url = f"{VIDEO_SERVICE_BASE_URL}/generate"
    data = {
        "prompt": prompt,
        "seed": str(seed),
        "seconds": str(seconds),
    }

    with image_path.open("rb") as image_file:
        files = {
            "image": (
                image_path.name,
                image_file,
                guess_upload_content_type(image_path),
            )
        }
        with requests.post(
            request_url,
            data=data,
            files=files,
            timeout=VIDEO_SERVICE_TIMEOUT_SECONDS,
            stream=True,
        ) as response:
            if not response.ok:
                raise RuntimeError(
                    f"Video generation service failed: {extract_video_service_error(response)}"
                )

            with output_path.open("wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output_file.write(chunk)


def concat_scene_videos(scene_video_paths: list[Path], output_path: Path) -> None:
    manifest_path = output_path.parent / "concat.txt"
    manifest_lines = "\n".join(f"file '{path.as_posix()}'" for path in scene_video_paths)
    manifest_path.write_text(manifest_lines, encoding="utf-8")

    commands = [
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            "-c",
            "copy",
            str(output_path),
        ],
        [
            FFMPEG_BIN,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
    ]
    last_error = "unknown ffmpeg error"

    for command in commands:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        last_error = result.stderr.strip() or result.stdout.strip() or last_error

    raise RuntimeError(f"Failed to concatenate scene videos: {last_error}")


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/download-final-video")
def download_final_video(asset_url: str, filename: str | None = None) -> FileResponse:
    try:
        asset_path = resolve_generated_asset_path(asset_url)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if asset_path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=400, detail="Only mp4 video downloads are supported")

    download_filename = (filename or asset_path.name).strip() or asset_path.name
    if not download_filename.lower().endswith(".mp4"):
        download_filename = f"{download_filename}.mp4"

    return FileResponse(
        path=asset_path,
        media_type="video/mp4",
        filename=download_filename,
    )


@app.post("/api/storyboard", response_model=StoryboardResponse)
def generate_storyboard(payload: StoryboardRequest) -> StoryboardResponse:
    try:
        parsed = request_llm_json(build_storyboard_prompt(payload), max_tokens=16384)
        storyboard = StoryboardResponse.model_validate(parsed)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate storyboard: {exc}",
        ) from exc

    if len(storyboard.scenes) != SCENE_COUNT:
        raise HTTPException(
            status_code=502,
            detail=f"Storyboard must contain exactly {SCENE_COUNT} scenes",
        )

    return storyboard


@app.post("/api/character-image", response_model=CharacterImageResponse)
def generate_character_image(payload: CharacterImageRequest) -> CharacterImageResponse:
    character_image_pipe = getattr(app.state, "character_image_pipe", None)
    if character_image_pipe is None:
        raise HTTPException(status_code=503, detail="Character image pipeline is not loaded")
    if payload.render_dimension != "real-person" and payload.style is None:
        raise HTTPException(status_code=400, detail="style is required for 2d or 3d character generation")

    prompt = compose_single_character_image_prompt(payload)
    summary = build_single_character_summary(payload)
    seed = uuid4().int % 2_147_483_647
    option_id = f"character-preview-{uuid4().hex}"

    try:
        with character_image_generation_lock:
            with torch.inference_mode():
                result = character_image_pipe(
                    prompt=prompt,
                    height=IMAGE_HEIGHT,
                    width=IMAGE_WIDTH,
                    num_inference_steps=CHARACTER_IMAGE_INFERENCE_STEPS,
                    generator=torch.Generator(device=CHARACTER_IMAGE_DEVICE).manual_seed(seed),
                )
        image_url = save_generated_image(result.images[0], option_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate character image: {exc}",
        ) from exc

    return CharacterImageResponse(
        image_url=image_url,
        prompt=prompt,
        summary=summary,
        render_dimension=payload.render_dimension,
        style=payload.style,
    )


@app.post("/api/character-designs", response_model=CharacterDesignResponse)
def generate_character_designs(payload: CharacterDesignRequest) -> CharacterDesignResponse:
    try:
        parsed = request_llm_json(build_character_prompt(payload), max_tokens=4096)
        prompt_response = CharacterPromptResponse.model_validate(parsed)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate character prompts: {exc}",
        ) from exc

    if len(prompt_response.options) != CHARACTER_OPTION_COUNT:
        raise HTTPException(
            status_code=502,
            detail=f"Character design response must contain exactly {CHARACTER_OPTION_COUNT} options",
        )

    character_image_pipe = getattr(app.state, "character_image_pipe", None)
    if character_image_pipe is None:
        raise HTTPException(status_code=503, detail="Character image pipeline is not loaded")

    design_options: list[CharacterDesignOption] = []
    seeds = [101, 202, 303]

    try:
        with character_image_generation_lock:
            for seed, option in zip(seeds, prompt_response.options):
                with torch.inference_mode():
                    result = character_image_pipe(
                        prompt=compose_character_image_prompt(option.prompt),
                        height=IMAGE_HEIGHT,
                        width=IMAGE_WIDTH,
                        num_inference_steps=CHARACTER_IMAGE_INFERENCE_STEPS,
                        generator=torch.Generator(device=CHARACTER_IMAGE_DEVICE).manual_seed(seed),
                    )
                option_id = uuid4().hex
                image_url = save_generated_image(result.images[0], option_id)
                design_options.append(
                    CharacterDesignOption(
                        option_id=option_id,
                        label=option.label,
                        summary=option.summary,
                        prompt=option.prompt,
                        image_url=image_url,
                        render_dimension="2d",
                        style="anime",
                    )
                )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate character images: {exc}",
        ) from exc

    return CharacterDesignResponse(
        character_summary=prompt_response.character_summary,
        options=design_options,
    )


@app.post("/api/scene-images", response_model=SceneImageResponse)
def generate_scene_images(payload: SceneImageRequest) -> SceneImageResponse:
    try:
        requested_scenes = get_requested_storyboard_scenes(payload.storyboard, payload.scene_indices)
        requested_scene_indices = [scene_index for scene_index, _scene in requested_scenes]
        parsed = request_llm_json(build_scene_image_prompt(payload), max_tokens=8192)
        prompt_response = SceneImagePromptResponse.model_validate(parsed)
        ordered_scene_prompts = order_scene_prompts(prompt_response, requested_scene_indices)
        reference_image_path = resolve_generated_asset_path(payload.selected_character.image_url)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to prepare scene image prompts: {exc}",
        ) from exc

    try:
        scene_image_pipe = get_scene_image_pipeline(app)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to load scene image pipeline: {exc}",
        ) from exc

    scene_images: list[SceneImageOption] = []

    try:
        with Image.open(reference_image_path) as selected_character_image:
            reference_character_image = selected_character_image.convert("RGB")

        with scene_image_generation_lock:
            for (_scene_index, scene), scene_prompt in zip(requested_scenes, ordered_scene_prompts):
                with torch.inference_mode():
                    result = scene_image_pipe(
                        prompt=scene_prompt.prompt,
                        image=reference_character_image.copy(),
                        height=IMAGE_HEIGHT,
                        width=IMAGE_WIDTH,
                        generator=torch.Generator(device=SCENE_IMAGE_DEVICE).manual_seed(
                            5000 + scene_prompt.scene_index
                        ),
                        num_inference_steps=SCENE_IMAGE_INFERENCE_STEPS,
                    )

                image_url = save_generated_image(
                    result.images[0],
                    f"scene-{scene_prompt.scene_index}-{uuid4().hex}",
                )
                scene_images.append(
                    SceneImageOption(
                        scene_index=scene_prompt.scene_index,
                        title=scene.title,
                        summary=scene.summary,
                        visual=scene.visual,
                        image_url=image_url,
                    )
                )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate scene images: {exc}",
        ) from exc

    return SceneImageResponse(scenes=scene_images)


@app.post("/api/final-video", response_model=FinalVideoResponse)
def generate_final_video(payload: FinalVideoRequest) -> FinalVideoResponse:
    expected_scene_count = len(payload.storyboard.scenes)

    try:
        ordered_scene_images = order_scene_images(payload.scenes, expected_scene_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        ordered_payload = payload.model_copy(update={"scenes": ordered_scene_images})
        parsed = request_llm_json(build_scene_video_prompt(ordered_payload), max_tokens=8192)
        prompt_response = SceneVideoPromptResponse.model_validate(parsed)
        scene_video_prompts = order_scene_prompts(
            prompt_response,
            [scene.scene_index for scene in ordered_scene_images],
        )
        scene_video_prompts = normalize_scene_video_prompts(scene_video_prompts)
        validate_scene_video_prompts(scene_video_prompts)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to prepare scene video prompts: {exc}",
        ) from exc

    job_dir = GENERATED_DIR / f"final-video-{uuid4().hex}"
    job_dir.mkdir(parents=True, exist_ok=True)
    scene_results: list[FinalVideoScene] = []
    scene_video_paths: list[Path] = []
    final_video_path = job_dir / "final-cut.mp4"

    try:
        for scene, scene_prompt in zip(ordered_scene_images, scene_video_prompts):
            image_path = resolve_generated_asset_path(scene.image_url)
            scene_video_path = job_dir / f"scene-{scene.scene_index:02d}.mp4"
            generate_scene_video_file(
                compose_scene_video_generation_prompt(scene_prompt),
                image_path,
                scene_video_path,
                seconds=payload.seconds_per_scene,
                seed=payload.seed + scene.scene_index,
            )
            scene_video_paths.append(scene_video_path)
            scene_results.append(
                FinalVideoScene(
                    scene_index=scene.scene_index,
                    title=scene.title,
                    summary=scene.summary,
                    image_url=scene.image_url,
                    video_url=build_generated_asset_url(scene_video_path),
                )
            )

        concat_scene_videos(scene_video_paths, final_video_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to generate final video: {exc}",
        ) from exc

    return FinalVideoResponse(
        video_url=build_generated_asset_url(final_video_path),
        scenes=scene_results,
    )
