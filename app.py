import asyncio
import io
import multiprocessing as mp
import os
import queue
import shutil
import sys
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from starlette.background import BackgroundTask

REPO_ROOT = "daVinci-MagiHuman"
CONFIG_PATH = f"{REPO_ROOT}/service_config_distill.json"
OUTPUT_DIR = "backend/video_outputs"
WORKER_GPU_IDS_ENV = "MAGIHUMAN_VIDEO_GPU_IDS"
MASTER_PORT_BASE = int(os.getenv("MAGIHUMAN_MASTER_PORT_BASE", "29501"))
WORKER_STARTUP_TIMEOUT_SECONDS = int(
    os.getenv("MAGIHUMAN_WORKER_STARTUP_TIMEOUT_SECONDS", "1800")
)

app = FastAPI(title="daVinci-MagiHuman API")
_worker_pool = None


def parse_gpu_ids(raw_value: str) -> list[int]:
    gpu_ids: list[int] = []

    for token in raw_value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        gpu_ids.append(int(stripped))

    if not gpu_ids:
        raise ValueError(f"{WORKER_GPU_IDS_ENV} must contain at least one GPU id")

    return gpu_ids


WORKER_GPU_IDS = parse_gpu_ids(os.getenv(WORKER_GPU_IDS_ENV, "0,1"))


@contextmanager
def patched_argv(extra_args: list[str]):
    original = sys.argv[:]
    sys.argv = [original[0]] + extra_args
    try:
        yield
    finally:
        sys.argv = original


def bootstrap_env(master_port: int):
    repo_root = str(Path(REPO_ROOT).resolve())

    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if repo_root not in current_pythonpath.split(":"):
        os.environ["PYTHONPATH"] = (
            f"{repo_root}:{current_pythonpath}" if current_pythonpath else repo_root
        )

    os.environ["MASTER_ADDR"] = "127.0.0.1"
    os.environ["MASTER_PORT"] = str(master_port)
    os.environ["RANK"] = "0"
    os.environ["WORLD_SIZE"] = "1"
    os.environ["LOCAL_RANK"] = "0"
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    os.environ.setdefault("NCCL_ALGO", "^NVLS")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def cleanup_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


class DaVinciMagiHumanService:
    def __init__(self, repo_root: str, config_path: str, master_port: int):
        bootstrap_env(master_port)
        self.repo_root = repo_root
        self.config_path = config_path
        self.lock = threading.Lock()

        from inference.common import parse_config
        from inference.infra import initialize_infra
        from inference.model.dit import get_dit
        from inference.pipeline.pipeline import MagiPipeline

        with patched_argv(["--config-load-path", config_path]):
            initialize_infra()
            config = parse_config()
            model = get_dit(config.arch_config, config.engine_config)
            self.pipeline = MagiPipeline(model, config.evaluation_config)

    def generate(
        self,
        prompt: str,
        image: Image.Image | str | Path,
        audio_path: Optional[str] = None,
        seed: int = 42,
        seconds: int = 4,
        br_width: int = 480,
        br_height: int = 272,
        sr_width: Optional[int] = None,
        sr_height: Optional[int] = None,
        output_width: Optional[int] = None,
        output_height: Optional[int] = None,
        upsample_mode: Optional[str] = None,
    ) -> str:
        request_id = uuid.uuid4().hex
        save_path_prefix = str(Path(OUTPUT_DIR) / request_id)

        if isinstance(image, (str, Path)):
            with Image.open(image) as opened_image:
                image = opened_image.convert("RGB")

        with self.lock:
            output_path = self.pipeline.run_offline(
                prompt=prompt,
                image=image,
                audio=audio_path,
                save_path_prefix=save_path_prefix,
                seed=seed,
                seconds=seconds,
                br_width=br_width,
                br_height=br_height,
                sr_width=sr_width,
                sr_height=sr_height,
                output_width=output_width,
                output_height=output_height,
                upsample_mode=upsample_mode,
            )
        return output_path


def video_worker_main(
    worker_index: int,
    gpu_id: int,
    repo_root: str,
    config_path: str,
    request_queue,
    ready_queue,
    response_queue,
):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    master_port = MASTER_PORT_BASE + worker_index

    try:
        service = DaVinciMagiHumanService(repo_root, config_path, master_port)
        ready_queue.put(
            {
                "status": "ready",
                "worker_index": worker_index,
                "gpu_id": gpu_id,
            }
        )
    except Exception as exc:
        ready_queue.put(
            {
                "status": "error",
                "worker_index": worker_index,
                "gpu_id": gpu_id,
                "error": f"{exc}\n{traceback.format_exc()}",
            }
        )
        return

    try:
        while True:
            task = request_queue.get()
            if task is None:
                break

            try:
                output_path = service.generate(
                    prompt=task["prompt"],
                    image=task["image_path"],
                    audio_path=task["audio_path"],
                    seed=task["seed"],
                    seconds=task["seconds"],
                    br_width=task["br_width"],
                    br_height=task["br_height"],
                    sr_width=task["sr_width"],
                    sr_height=task["sr_height"],
                    output_width=task["output_width"],
                    output_height=task["output_height"],
                    upsample_mode=task["upsample_mode"],
                )
                response_queue.put(
                    {
                        "request_id": task["request_id"],
                        "ok": True,
                        "output_path": output_path,
                        "worker_index": worker_index,
                        "gpu_id": gpu_id,
                    }
                )
            except Exception as exc:
                response_queue.put(
                    {
                        "request_id": task["request_id"],
                        "ok": False,
                        "error": str(exc),
                        "worker_index": worker_index,
                        "gpu_id": gpu_id,
                    }
                )
    finally:
        try:
            import torch

            if torch.distributed.is_initialized():
                torch.distributed.destroy_process_group()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


def _set_future_result(future: asyncio.Future, output_path: str) -> None:
    if not future.done():
        future.set_result(output_path)


def _set_future_exception(future: asyncio.Future, exc: Exception) -> None:
    if not future.done():
        future.set_exception(exc)


def _schedule_future_callback(future: asyncio.Future, callback, *args) -> None:
    try:
        future.get_loop().call_soon_threadsafe(callback, future, *args)
    except RuntimeError:
        pass


class GenerationWorkerPool:
    def __init__(self, repo_root: str, config_path: str, gpu_ids: list[int]):
        self.repo_root = repo_root
        self.config_path = config_path
        self.gpu_ids = gpu_ids
        self.ctx = mp.get_context("spawn")
        self.ready_queue = self.ctx.Queue()
        self.response_queue = self.ctx.Queue()
        self.request_queues = []
        self.processes = []
        self.pending: dict[str, asyncio.Future] = {}
        self.pending_lock = threading.Lock()
        self.dispatch_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.response_thread = None
        self.next_worker_index = 0

    def start(self) -> None:
        if self.processes:
            return

        self.stop_event.clear()
        self.response_thread = threading.Thread(
            target=self._response_listener,
            name="video-worker-response-listener",
            daemon=True,
        )
        self.response_thread.start()

        try:
            for worker_index, gpu_id in enumerate(self.gpu_ids):
                request_queue = self.ctx.Queue()
                process = self.ctx.Process(
                    target=video_worker_main,
                    args=(
                        worker_index,
                        gpu_id,
                        self.repo_root,
                        self.config_path,
                        request_queue,
                        self.ready_queue,
                        self.response_queue,
                    ),
                    daemon=True,
                )
                process.start()
                self.request_queues.append(request_queue)
                self.processes.append(process)

            self._wait_for_workers()
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        self.stop_event.set()

        for request_queue in self.request_queues:
            try:
                request_queue.put_nowait(None)
            except Exception:
                pass

        for process in self.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

        if self.response_thread is not None:
            self.response_thread.join(timeout=2)

        self._fail_pending_requests(RuntimeError("video worker pool is shutting down"))

        self.request_queues.clear()
        self.processes.clear()
        self.response_thread = None
        self.next_worker_index = 0

    def health_payload(self) -> dict:
        workers = []
        healthy = bool(self.processes)

        for worker_index, gpu_id in enumerate(self.gpu_ids):
            process = self.processes[worker_index] if worker_index < len(self.processes) else None
            alive = process.is_alive() if process is not None else False
            if not alive:
                healthy = False
            workers.append(
                {
                    "worker_index": worker_index,
                    "gpu_id": gpu_id,
                    "pid": process.pid if process is not None else None,
                    "alive": alive,
                }
            )

        return {
            "status": "ok" if healthy else "degraded",
            "workers": workers,
        }

    async def generate(
        self,
        *,
        prompt: str,
        image_path: str,
        audio_path: Optional[str],
        seed: int,
        seconds: int,
        br_width: int,
        br_height: int,
        sr_width: Optional[int],
        sr_height: Optional[int],
        output_width: Optional[int],
        output_height: Optional[int],
        upsample_mode: Optional[str],
    ) -> str:
        if not self.processes:
            raise RuntimeError("video worker pool is not started")

        request_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()

        with self.pending_lock:
            self.pending[request_id] = future

        worker_index = self._next_worker_index()

        task = {
            "request_id": request_id,
            "prompt": prompt,
            "image_path": image_path,
            "audio_path": audio_path,
            "seed": seed,
            "seconds": seconds,
            "br_width": br_width,
            "br_height": br_height,
            "sr_width": sr_width,
            "sr_height": sr_height,
            "output_width": output_width,
            "output_height": output_height,
            "upsample_mode": upsample_mode,
        }

        try:
            if not self.processes[worker_index].is_alive():
                raise RuntimeError(f"worker {worker_index} is not running")
            self.request_queues[worker_index].put(task)
        except Exception as exc:
            with self.pending_lock:
                self.pending.pop(request_id, None)
            raise RuntimeError(
                f"failed to dispatch request to worker {worker_index}: {exc}"
            ) from exc

        try:
            return await future
        except asyncio.CancelledError:
            with self.pending_lock:
                self.pending.pop(request_id, None)
            raise

    def _wait_for_workers(self) -> None:
        ready_workers: set[int] = set()
        deadline = time.monotonic() + WORKER_STARTUP_TIMEOUT_SECONDS

        while len(ready_workers) < len(self.gpu_ids):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("timed out while starting video workers")

            try:
                message = self.ready_queue.get(timeout=min(5, remaining))
            except queue.Empty:
                crashed = [
                    worker_index
                    for worker_index, process in enumerate(self.processes)
                    if worker_index not in ready_workers and not process.is_alive()
                ]
                if crashed:
                    raise RuntimeError(
                        f"video worker(s) crashed during startup: {', '.join(map(str, crashed))}"
                    )
                continue

            if message["status"] == "ready":
                ready_workers.add(message["worker_index"])
                continue

            raise RuntimeError(
                f"video worker {message['worker_index']} on GPU {message['gpu_id']} failed to start:\n{message['error']}"
            )

    def _response_listener(self) -> None:
        while not self.stop_event.is_set():
            try:
                message = self.response_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            request_id = message.get("request_id")
            if request_id is None:
                continue

            with self.pending_lock:
                future = self.pending.pop(request_id, None)

            if future is None:
                continue

            if message.get("ok"):
                _schedule_future_callback(
                    future,
                    _set_future_result,
                    message["output_path"],
                )
                continue

            _schedule_future_callback(
                future,
                _set_future_exception,
                RuntimeError(message.get("error", "video generation failed")),
            )

    def _fail_pending_requests(self, exc: Exception) -> None:
        with self.pending_lock:
            pending_items = list(self.pending.items())
            self.pending.clear()

        for _request_id, future in pending_items:
            _schedule_future_callback(future, _set_future_exception, exc)

    def _next_worker_index(self) -> int:
        with self.dispatch_lock:
            worker_index = self.next_worker_index
            self.next_worker_index = (self.next_worker_index + 1) % len(self.request_queues)
        return worker_index


@app.on_event("startup")
def startup_event():
    global _worker_pool
    _worker_pool = GenerationWorkerPool(REPO_ROOT, CONFIG_PATH, WORKER_GPU_IDS)
    _worker_pool.start()


@app.on_event("shutdown")
def shutdown_event():
    global _worker_pool
    if _worker_pool is not None:
        _worker_pool.stop()
        _worker_pool = None


@app.get("/health")
def health():
    if _worker_pool is None:
        return {"status": "starting", "workers": []}
    return _worker_pool.health_payload()


@app.post("/generate")
async def generate(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    ref_audio: Optional[UploadFile] = File(None),
    seed: int = Form(42),
    seconds: int = Form(4),
):
    if _worker_pool is None:
        raise HTTPException(status_code=500, detail="worker pool not initialized")

    if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=400, detail="image must be png/jpeg/webp")

    temp_dir = Path("/tmp") / f"magi_request_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    image_path = temp_dir / "image.png"
    temp_audio_path = None

    try:
        try:
            image_bytes = await image.read()
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            pil_image.save(image_path, format="PNG")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"invalid image: {exc}") from exc

        if ref_audio is not None:
            audio_suffix = Path(ref_audio.filename or "audio.bin").suffix or ".bin"
            temp_audio_path = str(temp_dir / f"audio{audio_suffix}")
            audio_bytes = await ref_audio.read()
            with open(temp_audio_path, "wb") as audio_file:
                audio_file.write(audio_bytes)

        output_path = await _worker_pool.generate(
            prompt=prompt,
            image_path=str(image_path),
            audio_path=temp_audio_path,
            seed=seed,
            seconds=seconds,
            br_width=480,
            br_height=272,
            sr_width=None,
            sr_height=None,
            output_width=None,
            output_height=None,
            upsample_mode=None,
        )

        return FileResponse(
            path=output_path,
            media_type="video/mp4",
            filename=Path(output_path).name,
            background=BackgroundTask(cleanup_directory, temp_dir),
        )
    except HTTPException:
        cleanup_directory(temp_dir)
        raise
    except Exception as exc:
        cleanup_directory(temp_dir)
        return JSONResponse(status_code=500, content={"error": str(exc)})
