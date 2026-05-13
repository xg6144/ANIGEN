import { useEffect, useRef, useState } from 'react'
import QRCode from 'qrcode'
import './App.css'
import injeUniversityLogo from './components/inje_university_logo.png'
import video1 from './components/video1.mp4'
import video2 from './components/video2.mp4'
import video3 from './components/video3.mp4'
import video4 from './components/video4.mp4'
import video5 from './components/video5.mp4'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const AVATAR_GRID_SIZE = 6
const STORYBOARD_SCENE_TARGET_COUNT = 6
const LANDING_HERO_VIDEOS = [
  { src: video1, title: 'ANIGEN Festival Preview 01' },
  { src: video2, title: 'ANIGEN Festival Preview 02' },
  { src: video3, title: 'ANIGEN Festival Preview 03' },
  { src: video4, title: 'ANIGEN Festival Preview 04' },
  { src: video5, title: 'ANIGEN Festival Preview 05' },
]
const CHARACTER_STYLE_OPTIONS = [
  {
    id: 'pixar',
    label: '픽사 (Pixar)',
    subtitle: '3D 정밀 렌더링 스타일',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuATkRJAqkLutLxDoImgMoTuooPkoRLH6SgJyWNCdN2W55J6oTeYa_vgYu6aEB-nKeWoPW8_FGFN6DGDMhwMkwS_Mfo0M1I_7pw93Z8D1YwcP2Y6wlNV3zM_5eAtuFBOF6bTN8ftQue6mEdVB37HonbsicDOpCzkO8juodqSwj1cPAdrm3SPdfjaR-DDJydxeS34OUVBKXc4QVfXfNFvtjo_zc-bks6inMcfuetOWeZ_OSoAsAI2xLMXENebw8Q6QKfj6CFhVBm1mnc',
    imageAlt: '픽사 스타일의 3D 캐릭터 초상',
    description: '입체적인 라이팅과 큰 감정 표현이 살아있는 페스티벌형 3D 캐릭터 스타일입니다.',
  },
  {
    id: 'disney',
    label: '디즈니 (Disney)',
    subtitle: '클래식 시네마틱 스타일',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCs7_fJz4M1vg_pybw3fm--OvsTfSV0wO5iM8XnZCf_VeR0m2D2FHEOfpvfkAsuAgqzeeVzVWWddxj6nQth1zJ7lsShgIvWaK2DxGvT3re2uTk9FF6MqyAyjCkCXMntS0y65-a0jeaG0lb4R8jtDfkhqWbhvQCOQRc0knhaJ99jTaKHoMxQHJhah7dv3ZkXDZYRWMFJMw15YxBmpAj8qHMtgQKXJLhjCbTwnGny52Bror6wrH0Pk8NCXKmoWLAZAIN6NL0xPAauI24',
    imageAlt: '부드러운 디즈니풍 캐릭터 초상',
    description: '부드러운 피부 표현과 극적인 조명으로 동화적인 감정을 강조하는 스타일입니다.',
  },
  {
    id: 'ghibli',
    label: '지브리 (Studio Ghibli)',
    subtitle: '수채화풍 감성 스타일',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCSeKd8ETfOTaK6acX0bzYt7BAUw0U0LGi5GfWksSFIReQupMrYBNS65NqPE2s26xM_x8S8ha4bVra_kMm833w6x4SEixqP0_zmNuLOMkWXVLzJ-mPlseNsSLtTnyu9eBOjr4rWZzBWCR6k-V3FV8thsAWaAWJgXURIDgx-3yg5_qgY87R_LKLanTvCTkcKu0y8-pobxJYPeaTzA6J7boz5M_yS58Sm1m3ernqX0kUxXKgG33rMNWa1MgJS4k2ZPnKDurF2Iw39e2A',
    imageAlt: '수채화풍 지브리 스타일 캐릭터 초상',
    description: '은은한 채색과 따뜻한 공기감을 담아 서정적인 분위기를 만드는 스타일입니다.',
  },
  {
    id: 'anime',
    label: '일본 애니메이션 스타일',
    subtitle: '선명한 셀 채색 스타일',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDMm0__k44R-zLhKOLv9FjnJnHp_FTR1DSUsCpP54Sc9n4zTxKlLzQVMe4tGq40qfCZaaPB-7cEgZEHvPpWo9xAqephHYpGdNbCRh9Hq9ZiFUewPDyKqYOpOYPOtOJM1-utFjG5m_KILrlqVa2FirpIEk2oJE89iTmM6FMUFVyO7wBnXLPkfZaci8MiPvxlyuFy_aI1euLjHxieh3eBtCQCwjlkNznzlCZsqkPWztV6Y35MjYDFmHmCs0I59MWn8aRTFKfPLleqpME',
    imageAlt: '선명한 일본 애니메이션 스타일 캐릭터 초상',
    description: '강한 라인과 명확한 명암으로 주인공성을 또렷하게 보여주는 셀 애니메이션 계열입니다.',
  },
  {
    id: 'korean-anime',
    label: '한국 애니메이션 스타일',
    subtitle: '세련된 트렌디 웹툰 스타일',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBGl0jtVETdYX5adZBzRcy1UsjYQkx5Kk-MEZp8Pp626R5jKswz26uqr_K09W9rbM7o41ECJFNkcs8DdNQZP5OBK4CZfuXb2xFmPYGLVG08ouibDk6ctKBbInGVty9K5dhLkZbNlHy63rEdoL0jlcBUgiPoY8eWLCY-dvXKLOF27vMl4428Jv9ZekEeDjQ28xbHLB_jpLwM8hf3bAIzKnxcpqX7fy0Agwtr3utvLeVv5POnXb7WRHZEqXHKmVMI14sBvt06oq4i5DA',
    imageAlt: '트렌디한 한국 애니메이션 스타일 캐릭터 초상',
    description: '현대적인 색감과 웹툰 감성으로 밝고 또렷한 캐릭터 톤을 만드는 스타일입니다.',
  },
  {
    id: '3d',
    label: '3D',
    subtitle: '입체적인 디지털 아트',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB351leMx5xWrJiBgkTJDYPRDHRQmtJiOD8Ymme_zHVaC6G9lbqpkUl7zN5o4qNht4iBvNAEC4DeaDnsUZHWPhVR5_TOulaThdKGBFvI_9CZI0N5WNSR2qUa_UHIs08_3xubSkJD6IU0ik-YNaz3erYJ2zvU29EvcB-WiHx567wN5wR-YcsNCH4_laKWfSmxeZKSkUQdw_7O3hjkykXf3rLggBhnOjOqzaMUNiqwUtwZz4EmIm7mggpZ4Yxmd0_Z9ZswAhACipy5ek',
    imageAlt: '현대적인 3D 디지털 아트 캐릭터 초상',
    description: '질감이 풍부한 디지털 아트 기반으로 실험적인 조형감을 강조하는 스타일입니다.',
  },
  {
    id: 'photo',
    label: '실사 (Photorealistic)',
    subtitle: '초고해상도 실사 스타일',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDRmM88JEjo02_-6rhSUVbvk3KSqdm6xwDCJBQOJFofcAXSlEbNr2mUm-SoMLA92Pgdf0XY3JJ1hBMD2Z1EO3u-ePzvvrvGkoruy6h17DSSyAiLHXGIJ62mwu4qOpH3l3libUgAEYBZ5jX2JV67jjmgX7eaJ5fGChFI2OpzspjmTcWcB-WNrbvYKNK6ZlwQHRzALfL1CJ3l4cMpQN9d8plYN87tEVs_LzGCQMNkPQuvubWHOe6gAVy61nRCeusUMtLKTiyoBdrekmQ',
    imageAlt: '사실적인 실사풍 캐릭터 초상',
    description: '고해상도 피부 질감과 현실적인 조명으로 인물 중심 아바타를 표현하는 스타일입니다.',
  },
]

function App() {
  const storyboardBackgroundSectionRef = useRef(null)
  const storyboardBackgroundPromptRef = useRef(null)
  const storyboardEventSectionRef = useRef(null)
  const storyboardEventPromptRef = useRef(null)
  const storyboardResultSectionRef = useRef(null)
  const shouldScrollToStoryboardResultRef = useRef(false)
  const [screen, setScreen] = useState('landing')
  const [character, setCharacter] = useState('')
  const [background, setBackground] = useState('')
  const [event, setEvent] = useState('')
  const [storyboard, setStoryboard] = useState(null)
  const [characterDesigns, setCharacterDesigns] = useState(null)
  const [generatedCharacterResults, setGeneratedCharacterResults] = useState([])
  const [generatedCharacterResult, setGeneratedCharacterResult] = useState(null)
  const [sceneImages, setSceneImages] = useState(null)
  const [finalVideo, setFinalVideo] = useState(null)
  const [selectedCharacterOptionId, setSelectedCharacterOptionId] = useState('')
  const [selectedAvatarStyleId, setSelectedAvatarStyleId] = useState(CHARACTER_STYLE_OPTIONS[0].id)
  const [loadingSceneIndices, setLoadingSceneIndices] = useState([])
  const [loadingMode, setLoadingMode] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [expandedAvatarPreview, setExpandedAvatarPreview] = useState(null)
  const [expandedScenePreview, setExpandedScenePreview] = useState(null)
  const [isDownloadQrModalOpen, setIsDownloadQrModalOpen] = useState(false)
  const [downloadQrCodeDataUrl, setDownloadQrCodeDataUrl] = useState('')
  const [downloadQrCodeError, setDownloadQrCodeError] = useState('')
  const [activeStoryboardSceneIndex, setActiveStoryboardSceneIndex] = useState(0)

  const isGlobalLoading = loadingMode !== ''
  const isCharacterImageLoading = loadingMode === 'character-image'
  const isAnySceneCardLoading = loadingSceneIndices.length > 0
  const loadingContent =
    loadingMode === 'character-image'
      ? {
        eyebrow: 'CHARACTER',
        title: '주인공 이미지를 만들고 있어요',
        copy: '선택한 캐릭터 형식과 스타일 조건을 반영해 주인공 이미지 1장을 생성하고 있습니다.',
      }
      : loadingMode === 'scene-images'
        ? {
          eyebrow: 'SCENE VISUALS',
          title: '장면 이미지를 만들고 있어요',
          copy: '참조 주인공 이미지를 기반으로 선택한 장면을 image-to-image 방식으로 생성하고 있습니다.',
        }
        : loadingMode === 'final-video'
          ? {
            eyebrow: 'FINAL CUT',
            title: '장면을 영상으로 엮고 있어요',
            copy: '각 장면 이미지를 영상으로 변환한 뒤 하나의 완성된 애니메이션으로 병합하고 있습니다.',
          }
          : loadingMode === 'character-designs'
            ? {
              eyebrow: 'CHARACTER DESIGN',
              title: '주인공 시안을 만들고 있어요',
              copy: '생성된 스토리보드를 분석해 일본 애니메이션 주인공 스타일 외형 시안 3개를 만들고 있습니다.',
            }
            : {
              eyebrow: 'GENERATING',
              title: '스토리보드를 만들고 있어요',
              copy: '주인공, 배경, 사건을 바탕으로 장면 구성을 정리하고 있습니다.',
            }

  const selectedCharacterOption = characterDesigns?.options?.find(
    (option) => option.option_id === selectedCharacterOptionId,
  )
  const isLandingScreen = screen === 'landing'
  const isFestivalChromeScreen =
    isLandingScreen || screen === 'character' || screen === 'storyboard' || screen === 'final-video'
  const isTechScreen = screen === 'character-design'
  const techScreenHeaderLabel = screen === 'character-design' ? 'CHARACTER DESIGN' : 'CHARACTER STUDIO'
  const generatedReferenceCharacter = generatedCharacterResult
    ? {
      label: '선택한 주인공 이미지',
      summary: generatedCharacterResult.summary,
      prompt: generatedCharacterResult.prompt,
      image_url: generatedCharacterResult.image_url,
      render_dimension: generatedCharacterResult.render_dimension,
      style: generatedCharacterResult.style,
    }
    : null
  const selectedReferenceCharacter = generatedReferenceCharacter ?? selectedCharacterOption
  const selectedAvatarStyle = CHARACTER_STYLE_OPTIONS.find(
    (styleOption) => styleOption.id === selectedAvatarStyleId,
  ) ?? CHARACTER_STYLE_OPTIONS[0]
  const characterGridSlots = Array.from(
    { length: AVATAR_GRID_SIZE },
    (_unused, index) => generatedCharacterResults[index] ?? null,
  )
  const isCharacterGridFull = generatedCharacterResults.length >= AVATAR_GRID_SIZE
  const characterGridLoadingSlotIndex = isCharacterImageLoading && !isCharacterGridFull
    ? generatedCharacterResults.length
    : -1
  const hasGeneratedCharacterPreview = Boolean(generatedCharacterResult?.image_url)
  const storyboardScenes = storyboard?.scenes ?? []
  const generatedStoryboardSceneIndexSet = new Set(
    (sceneImages ?? []).map((sceneImage) => sceneImage.scene_index),
  )
  const generatedStoryboardSceneCount = storyboardScenes.reduce(
    (count, _scene, index) => (generatedStoryboardSceneIndexSet.has(index + 1) ? count + 1 : count),
    0,
  )
  const hasAllStoryboardSceneImages =
    storyboardScenes.length === STORYBOARD_SCENE_TARGET_COUNT &&
    generatedStoryboardSceneCount === STORYBOARD_SCENE_TARGET_COUNT
  const activeStoryboardScene = storyboardScenes[activeStoryboardSceneIndex] ?? null
  const activeStoryboardSceneNumber = activeStoryboardSceneIndex + 1
  const activeGeneratedScene = activeStoryboardScene
    ? sceneImages?.find((sceneImage) => sceneImage.scene_index === activeStoryboardSceneNumber)
    : null
  const isActiveStoryboardSceneLoading = activeStoryboardScene
    ? loadingSceneIndices.includes(activeStoryboardSceneNumber)
    : false
  const handleReturnHome = () => {
    setScreen('landing')
    setErrorMessage('')
    setExpandedAvatarPreview(null)
    setExpandedScenePreview(null)
    setIsDownloadQrModalOpen(false)
  }
  const resetStoryboardPipeline = ({ clearStoryboard = true } = {}) => {
    if (clearStoryboard) {
      setStoryboard(null)
    }

    setCharacterDesigns(null)
    setSceneImages(null)
    setFinalVideo(null)
    setSelectedCharacterOptionId('')
    setLoadingSceneIndices([])
    setExpandedScenePreview(null)
    setIsDownloadQrModalOpen(false)
    setDownloadQrCodeDataUrl('')
    setDownloadQrCodeError('')
  }

  const handleGoToStoryboard = () => {
    if (!hasGeneratedCharacterPreview) {
      setErrorMessage('생성된 이미지 중 하나를 선택해주세요.')
      return
    }

    setScreen('storyboard')
    setErrorMessage('')
  }

  const handleScrollToBackgroundPrompt = () => {
    storyboardBackgroundSectionRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })

    window.setTimeout(() => {
      storyboardBackgroundPromptRef.current?.focus({ preventScroll: true })
    }, 420)
  }

  const handleScrollToEventPrompt = () => {
    storyboardEventSectionRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })

    window.setTimeout(() => {
      storyboardEventPromptRef.current?.focus({ preventScroll: true })
    }, 420)
  }

  useEffect(() => {
    if (!storyboard || loadingMode !== '' || !shouldScrollToStoryboardResultRef.current) {
      return
    }

    shouldScrollToStoryboardResultRef.current = false
    storyboardResultSectionRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }, [loadingMode, storyboard])

  useEffect(() => {
    setActiveStoryboardSceneIndex(0)
  }, [storyboard])

  const handleSelectAvatarStyle = (styleId) => {
    setSelectedAvatarStyleId(styleId)
    setErrorMessage('')
  }
  const renderLoadingSpinner = ({ className = '', variant = 'default' } = {}) => (
    variant === 'festival-avatar'
      ? (
        <div className={`loading-spinner loading-spinner-festival ${className}`.trim()} aria-hidden="true">
          <span className="loading-spinner-festival-ring" />
          <span className="loading-spinner-festival-node">
            <span className="material-symbols-outlined loading-spinner-festival-icon">
              auto_awesome
            </span>
          </span>
        </div>
      )
      : (
        <div className={`loading-spinner ${className}`.trim()} aria-hidden="true">
          <span className="spinner-ring spinner-ring-outer" />
          <span className="spinner-ring spinner-ring-middle" />
          <span className="spinner-ring spinner-ring-inner" />
          <span className="spinner-core" />
        </div>
      )
  )

  function resolveAssetUrl(path) {
    if (!path) {
      return ''
    }

    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path
    }

    return `${API_BASE_URL}${path}`
  }

  function resolveAbsoluteAssetUrl(path) {
    const resolvedPath = resolveAssetUrl(path)

    if (!resolvedPath) {
      return ''
    }

    if (resolvedPath.startsWith('http://') || resolvedPath.startsWith('https://')) {
      return resolvedPath
    }

    return new URL(resolvedPath, window.location.origin).toString()
  }

  function buildFinalVideoDownloadUrl(videoAssetUrl) {
    if (!videoAssetUrl) {
      return ''
    }

    const query = new URLSearchParams({
      asset_url: videoAssetUrl,
      filename: 'anigen-final-video.mp4',
    })

    return resolveAbsoluteAssetUrl(`/api/download-final-video?${query.toString()}`)
  }

  const finalVideoDownloadUrl = finalVideo?.video_url
    ? buildFinalVideoDownloadUrl(finalVideo.video_url)
    : ''

  const handleStart = () => {
    setErrorMessage('')
    setScreen('character')
  }

  const clearGeneratedCharacterResult = () => {
    setGeneratedCharacterResults([])
    setGeneratedCharacterResult(null)
    setExpandedAvatarPreview(null)
  }

  const handleCharacterChange = (value) => {
    setCharacter(value)
    setErrorMessage('')
  }

  const handleBackgroundChange = (value) => {
    setBackground(value)
    setErrorMessage('')
    resetStoryboardPipeline()
  }

  const handleEventChange = (value) => {
    setEvent(value)
    setErrorMessage('')
    resetStoryboardPipeline()
  }

  const handleResetGeneratedCharacterWorkspace = () => {
    setCharacter('')
    setBackground('')
    setEvent('')
    setErrorMessage('')
    clearGeneratedCharacterResult()
    resetStoryboardPipeline()
  }

  const handleSelectGeneratedCharacterResult = (result) => {
    if (generatedCharacterResult?.image_url !== result.image_url) {
      setSceneImages(null)
      setFinalVideo(null)
      setLoadingSceneIndices([])
    }

    setGeneratedCharacterResult(result)
    setErrorMessage('')
  }

  const handleRemoveGeneratedCharacterResult = (candidateToRemove) => {
    setGeneratedCharacterResults((currentResults) => (
      currentResults.filter((result) => result.image_url !== candidateToRemove.image_url)
    ))

    if (generatedCharacterResult?.image_url === candidateToRemove.image_url) {
      setGeneratedCharacterResult(null)
      setSceneImages(null)
      setFinalVideo(null)
      setLoadingSceneIndices([])
    }

    if (expandedAvatarPreview?.candidate?.image_url === candidateToRemove.image_url) {
      setExpandedAvatarPreview(null)
    }

    setErrorMessage('')
  }

  const handleOpenExpandedAvatarPreview = (candidate, index) => {
    setExpandedAvatarPreview({
      candidate,
      index,
    })
  }

  const handleCloseExpandedAvatarPreview = () => {
    setExpandedAvatarPreview(null)
  }

  const handleOpenExpandedScenePreview = (scene) => {
    setExpandedScenePreview({
      image_url: scene.image_url,
      title: scene.title,
      scene_index: scene.scene_index,
    })
  }

  const handleCloseExpandedScenePreview = () => {
    setExpandedScenePreview(null)
  }

  const handleOpenDownloadQrModal = () => {
    if (!finalVideoDownloadUrl) {
      return
    }

    setDownloadQrCodeError('')
    setIsDownloadQrModalOpen(true)
  }

  const handleCloseDownloadQrModal = () => {
    setIsDownloadQrModalOpen(false)
  }

  useEffect(() => {
    if (!expandedAvatarPreview && !expandedScenePreview && !isDownloadQrModalOpen) {
      return undefined
    }

    const handleWindowKeyDown = (eventObject) => {
      if (eventObject.key === 'Escape') {
        setExpandedAvatarPreview(null)
        setExpandedScenePreview(null)
        setIsDownloadQrModalOpen(false)
      }
    }

    window.addEventListener('keydown', handleWindowKeyDown)
    return () => {
      window.removeEventListener('keydown', handleWindowKeyDown)
    }
  }, [expandedAvatarPreview, expandedScenePreview, isDownloadQrModalOpen])

  useEffect(() => {
    if (!isDownloadQrModalOpen || !finalVideoDownloadUrl) {
      return undefined
    }

    let isCancelled = false

    setDownloadQrCodeDataUrl('')
    setDownloadQrCodeError('')

    QRCode.toDataURL(finalVideoDownloadUrl, {
      width: 320,
      margin: 1,
      color: {
        dark: '#001648',
        light: '#0000',
      },
    })
      .then((generatedDataUrl) => {
        if (!isCancelled) {
          setDownloadQrCodeDataUrl(generatedDataUrl)
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setDownloadQrCodeError('QR 코드 생성에 실패했습니다. 잠시 후 다시 시도해주세요.')
        }
      })

    return () => {
      isCancelled = true
    }
  }, [finalVideoDownloadUrl, isDownloadQrModalOpen])

  const handleGenerateCharacterImage = async () => {
    const trimmedCharacter = character.trim()

    if (!trimmedCharacter) {
      setErrorMessage('주인공 설명을 먼저 입력해주세요.')
      return
    }

    if (isCharacterGridFull) {
      setErrorMessage(`주인공 이미지는 최대 ${AVATAR_GRID_SIZE}장까지 생성할 수 있습니다.`)
      return
    }

    const generationPreset = selectedAvatarStyleId === 'pixar'
      ? { render_dimension: '3d', style: 'pixar' }
      : selectedAvatarStyleId === '3d'
        ? { render_dimension: '3d', style: 'pixar' }
        : selectedAvatarStyleId === 'photo'
          ? { render_dimension: 'real-person', style: null }
          : { render_dimension: '2d', style: 'anime' }

    setLoadingMode('character-image')
    setErrorMessage('')
    resetStoryboardPipeline({ clearStoryboard: false })

    try {
      const response = await fetch(`${API_BASE_URL}/api/character-image`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character: trimmedCharacter,
          advanced_prompt: '',
          ...generationPreset,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '주인공 이미지 생성에 실패했습니다.')
      }

      setGeneratedCharacterResults((currentResults) => [...currentResults, data])
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.',
      )
    } finally {
      setLoadingMode('')
    }
  }

  const handleGenerateFinalVideo = async (currentSceneImages = sceneImages) => {
    if (!storyboard) {
      setErrorMessage('스토리보드가 먼저 생성되어야 합니다.')
      return
    }

    if (!selectedReferenceCharacter) {
      setErrorMessage('주인공 이미지를 먼저 생성해주세요.')
      return
    }

    const currentSceneImageIndexSet = new Set(
      (currentSceneImages ?? []).map((sceneImage) => sceneImage.scene_index),
    )
    const hasAllSceneImages =
      storyboardScenes.length === STORYBOARD_SCENE_TARGET_COUNT &&
      storyboardScenes.every((_scene, index) => currentSceneImageIndexSet.has(index + 1))

    if (!hasAllSceneImages) {
      setErrorMessage(`영상을 생성하려면 ${STORYBOARD_SCENE_TARGET_COUNT}개의 장면 이미지가 모두 필요합니다.`)
      return
    }

    setLoadingMode('final-video')
    setErrorMessage('')
    setIsDownloadQrModalOpen(false)

    try {
      const response = await fetch(`${API_BASE_URL}/api/final-video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character,
          background,
          event,
          storyboard,
          selected_character: selectedReferenceCharacter,
          scenes: currentSceneImages,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '최종 영상 생성에 실패했습니다.')
      }

      setFinalVideo(data)
      setScreen('final-video')
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.',
      )
      setScreen('scene-images')
    } finally {
      setLoadingMode('')
    }
  }

  const handleGenerateStoryboard = async () => {
    const trimmedCharacter = character.trim()
    const trimmedBackground = background.trim()
    const trimmedEvent = event.trim()

    if (!trimmedCharacter) {
      setErrorMessage('주인공 설명이 먼저 준비되어야 합니다.')
      setScreen('character')
      return
    }

    if (!trimmedBackground) {
      setErrorMessage('배경을 먼저 입력해주세요.')
      return
    }

    if (!trimmedEvent) {
      setErrorMessage('사건을 먼저 입력해주세요.')
      return
    }

    setLoadingMode('storyboard')
    setErrorMessage('')
    shouldScrollToStoryboardResultRef.current = true
    resetStoryboardPipeline()

    try {
      const response = await fetch(`${API_BASE_URL}/api/storyboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character: trimmedCharacter,
          background: trimmedBackground,
          event: trimmedEvent,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '스토리보드 생성에 실패했습니다.')
      }

      setStoryboard(data)
      setScreen('storyboard')
    } catch (error) {
      shouldScrollToStoryboardResultRef.current = false
      setErrorMessage(
        error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.',
      )
    } finally {
      setLoadingMode('')
    }
  }

  const handleGenerateCharacterDesigns = async () => {
    if (!storyboard) {
      setErrorMessage('스토리보드가 먼저 생성되어야 합니다.')
      return
    }

    setLoadingMode('character-designs')
    setErrorMessage('')
    setSceneImages(null)
    setFinalVideo(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/character-designs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          character,
          background,
          event,
          storyboard,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '주인공 시안 생성에 실패했습니다.')
      }

      setCharacterDesigns(data)
      setSelectedCharacterOptionId(data.options?.[0]?.option_id ?? '')
      setScreen('character-design')
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.',
      )
    } finally {
      setLoadingMode('')
    }
  }

  const handleSelectCharacterOption = (optionId) => {
    setSelectedCharacterOptionId(optionId)
    setSceneImages(null)
    setFinalVideo(null)
  }

  const handleOpenCharacterDesignPage = () => {
    if (!storyboard) {
      setErrorMessage('스토리보드가 먼저 생성되어야 합니다.')
      return
    }

    setErrorMessage('')
    setScreen('character-design')
  }

  const handleOpenSceneImagesPage = () => {
    if (!selectedReferenceCharacter) {
      setErrorMessage('주인공 이미지를 먼저 생성해주세요.')
      return
    }

    setErrorMessage('')
    setScreen('scene-images')
  }

  const mergeSceneImages = (newScenes) => {
    setSceneImages((currentSceneImages) => {
      const sceneMap = new Map((currentSceneImages ?? []).map((scene) => [scene.scene_index, scene]))
      newScenes.forEach((scene) => {
        sceneMap.set(scene.scene_index, scene)
      })

      return Array.from(sceneMap.values()).sort((sceneA, sceneB) => (
        sceneA.scene_index - sceneB.scene_index
      ))
    })
  }

  const handleGenerateSceneImages = async (sceneIndex = null) => {
    if (!storyboard) {
      setErrorMessage('스토리보드가 먼저 생성되어야 합니다.')
      return
    }

    if (!selectedReferenceCharacter) {
      setErrorMessage('주인공 이미지를 먼저 생성해주세요.')
      return
    }

    if (sceneIndex !== null && loadingSceneIndices.includes(sceneIndex)) {
      return
    }

    setErrorMessage('')
    setFinalVideo(null)

    if (sceneIndex === null) {
      setLoadingMode('scene-images')
    } else {
      setLoadingSceneIndices((currentSceneIndices) => (
        currentSceneIndices.includes(sceneIndex)
          ? currentSceneIndices
          : [...currentSceneIndices, sceneIndex]
      ))
    }

    try {
      const requestBody = {
        character,
        background,
        event,
        storyboard,
        selected_character: selectedReferenceCharacter,
      }

      if (sceneIndex !== null) {
        requestBody.scene_indices = [sceneIndex]
      }

      const response = await fetch(`${API_BASE_URL}/api/scene-images`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '장면 이미지 생성에 실패했습니다.')
      }

      const generatedScenes = data.scenes ?? []
      mergeSceneImages(generatedScenes)

      if (sceneIndex === null) {
        setScreen('scene-images')
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.',
      )
    } finally {
      if (sceneIndex === null) {
        setLoadingMode('')
      } else {
        setLoadingSceneIndices((currentSceneIndices) => (
          currentSceneIndices.filter((currentSceneIndex) => currentSceneIndex !== sceneIndex)
        ))
      }
    }
  }

  const festivalFooter = (
    <footer className="festival-footer">
      <div className="festival-shell festival-footer-inner">
        <div className="festival-footer-brand">A N I G E N</div>
        <div className="festival-footer-links">
          <a href="mailto:dbjeon@inje.ac.kr">Contact US: dbjeon@inje.ac.kr</a>
          <button className="festival-footer-link-button" type="button" onClick={handleReturnHome}>
            이용약관
          </button>
          <button className="festival-footer-link-button" type="button" onClick={handleReturnHome}>
            개인정보처리방침
          </button>
        </div>
        <div className="festival-footer-copy">
          © 2026 A N I G E N. All rights reserved.
        </div>
      </div>
    </footer>
  )

  return (
    <main className={`app-shell${isTechScreen ? ' app-shell-landing' : ''}${isFestivalChromeScreen ? ' app-shell-festival' : ''}`}>
      {isFestivalChromeScreen ? (
        <header className="festival-header">
          <div className="festival-shell festival-header-inner">
            <button className="festival-brand festival-brand-button" type="button" onClick={handleReturnHome}>
              A N I G E N
            </button>
            <div className="app-header-logo" aria-label="인제대학교 로고">
              <img className="app-header-logo-image" src={injeUniversityLogo} alt="인제대학교 로고" />
            </div>
          </div>
        </header>
      ) : (
        <header className={`header-bar${isTechScreen ? ' header-bar-landing' : ''}`}>
          <button
            className={`brand-name brand-name-btn${isTechScreen ? ' brand-name-landing' : ''}`}
            type="button"
            onClick={() => { setScreen('landing'); setErrorMessage('') }}
          >
            ANIGEN
          </button>
          {isTechScreen ? (
            <div className="landing-header-actions">
              <span className="landing-status-inline">
                <span className="landing-status-pulse" />
                {techScreenHeaderLabel}
              </span>
            </div>
          ) : null}
          <div className="app-header-logo" aria-label="인제대학교 로고">
            <img className="app-header-logo-image" src={injeUniversityLogo} alt="인제대학교 로고" />
          </div>
        </header>
      )}

      {isLandingScreen ? (
        <>
          <section className="festival-hero festival-section" id="landing-overview">
            <div className="festival-shell festival-hero-grid">
              <div className="festival-hero-copy">
                <div className="festival-badge">대한민국 과학축제 - 김해 생활과학교실</div>
                <h1 className="festival-title">
                  나만의
                  <br />
                  애니메이션,
                  <br />
                  <span>AI로 완성하다</span>
                </h1>
                <p className="festival-description">
                  누구나 AI를 이용해서 쉽게 만드는 애니메이션을 체험해보세요!
                </p>

                <div className="festival-actions">
                  <button className="festival-primary-button" type="button" onClick={handleStart}>
                    시작하기
                  </button>
                </div>
              </div>

              <div className="festival-hero-visual">
                <div
                  className="festival-hero-video-marquee festival-hero-image-frame"
                  aria-label="인공지능 스튜디오 체험 영상 미리보기"
                >
                  <div className="festival-hero-video-track">
                    {[...LANDING_HERO_VIDEOS, ...LANDING_HERO_VIDEOS].map((video, index) => (
                      <article
                        key={`${video.title}-${index}`}
                        className="festival-hero-video-card"
                        aria-hidden={index >= LANDING_HERO_VIDEOS.length}
                      >
                        <video
                          className="festival-hero-video"
                          src={video.src}
                          autoPlay
                          loop
                          muted
                          playsInline
                          preload="metadata"
                        />
                      </article>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {festivalFooter}
        </>
      ) : screen === 'character' ? (
        <>
          <section className="festival-avatar-page festival-section">
            <div className="festival-shell festival-avatar-shell">
              <aside className="festival-avatar-sidebar" aria-label="아바타 스타일 선택">
                <div className="festival-avatar-sidebar-head">
                  <h2 className="festival-avatar-sidebar-title">스타일</h2>
                  <button
                    className="festival-avatar-sidebar-reset-button"
                    type="button"
                    onClick={handleResetGeneratedCharacterWorkspace}
                  >
                    <span className="material-symbols-outlined">restart_alt</span>
                    <span>초기화</span>
                  </button>
                </div>

                <div className="festival-avatar-style-list">
                  {CHARACTER_STYLE_OPTIONS.map((styleOption) => (
                    <button
                      key={styleOption.id}
                      className={`festival-avatar-style-item${selectedAvatarStyle.id === styleOption.id
                        ? ' festival-avatar-style-item-active'
                        : ''
                        }`}
                      type="button"
                      aria-pressed={selectedAvatarStyle.id === styleOption.id}
                      onClick={() => handleSelectAvatarStyle(styleOption.id)}
                    >
                      <img
                        className="festival-avatar-style-image"
                        src={styleOption.imageUrl}
                        alt={styleOption.imageAlt}
                      />
                      <div className="festival-avatar-style-copy">
                        <span className="festival-avatar-style-name">{styleOption.label}</span>
                        <span className="festival-avatar-style-subtitle">{styleOption.subtitle}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </aside>

              <section className="festival-avatar-main">
                <div className="festival-avatar-canvas" role="list" aria-label="생성된 주인공 이미지 선택 그리드">
                  {characterGridSlots.map((candidate, index) => {
                    const isLoadingSlot = characterGridLoadingSlotIndex === index
                    const isSelected = candidate?.image_url === generatedCharacterResult?.image_url

                    return (
                      <div
                        key={candidate?.image_url ?? `avatar-grid-slot-${index + 1}`}
                        className={`festival-avatar-grid-cell${candidate ? ' festival-avatar-grid-cell-filled' : ''}${isSelected ? ' festival-avatar-grid-cell-selected' : ''}${isLoadingSlot ? ' festival-avatar-grid-cell-loading' : ''}`}
                        role="listitem"
                      >
                        {candidate ? (
                          <button
                            className="festival-avatar-grid-select-button"
                            type="button"
                            aria-pressed={isSelected}
                            aria-label={`생성된 주인공 이미지 ${index + 1}번 선택`}
                            onClick={() => {
                              handleSelectGeneratedCharacterResult(candidate)
                            }}
                          />
                        ) : null}

                        <span className="festival-avatar-grid-cell-index">
                          {String(index + 1).padStart(2, '0')}
                        </span>

                        {candidate ? (
                          <>
                            <button
                              className="festival-avatar-grid-delete-button"
                              type="button"
                              aria-label={`생성된 주인공 이미지 ${index + 1}번 삭제`}
                              onClick={(eventObject) => {
                                eventObject.stopPropagation()
                                handleRemoveGeneratedCharacterResult(candidate)
                              }}
                            >
                              <span className="material-symbols-outlined">delete</span>
                            </button>
                            <button
                              className="festival-avatar-grid-zoom-button"
                              type="button"
                              aria-label={`생성된 주인공 이미지 ${index + 1}번 확대 보기`}
                              onClick={(eventObject) => {
                                eventObject.stopPropagation()
                                handleOpenExpandedAvatarPreview(candidate, index)
                              }}
                            >
                              <span className="material-symbols-outlined">search</span>
                            </button>
                            <img
                              className="festival-avatar-grid-image"
                              src={resolveAssetUrl(candidate.image_url)}
                              alt={`생성된 주인공 후보 ${index + 1}`}
                            />
                            <span className="festival-avatar-grid-cell-badge">
                              {isSelected ? '선택됨' : '선택'}
                            </span>
                          </>
                        ) : null}

                        {!candidate && !isLoadingSlot ? (
                          <span className="festival-avatar-grid-empty-copy">빈 슬롯</span>
                        ) : null}

                        {isLoadingSlot ? (
                          <span className="festival-avatar-grid-loading-shell">
                            {renderLoadingSpinner({
                              variant: 'festival-avatar',
                              className: 'festival-avatar-grid-loading-spinner',
                            })}
                            <span className="festival-avatar-grid-loading-copy">생성 중</span>
                          </span>
                        ) : null}
                      </div>
                    )
                  })}
                </div>

                <div className="festival-avatar-prompt-panel">
                  <label className="festival-avatar-prompt-label" htmlFor="character">
                    주인공 묘사 입력 (Prompt)
                  </label>
                  <div className="festival-avatar-prompt-shell">
                    <textarea
                      id="character"
                      className="festival-avatar-prompt-input"
                      placeholder="예: 안경을 쓰고 책을 읽고 있는 밝은 표정의 대학생..."
                      aria-label="주인공 프롬프트 입력"
                      value={character}
                      onChange={(eventObject) => handleCharacterChange(eventObject.target.value)}
                    />
                  </div>
                </div>

                <div className="festival-avatar-bottom-row">
                  <div className="festival-avatar-action-group">
                    <button
                      className="festival-avatar-generate-button"
                      type="button"
                      onClick={handleGenerateCharacterImage}
                      disabled={!character.trim() || isGlobalLoading || isCharacterGridFull}
                    >
                      {isCharacterImageLoading
                        ? '이미지 생성 중...'
                        : isCharacterGridFull
                          ? `${AVATAR_GRID_SIZE}개 이미지 완료`
                          : '이미지 생성하기'}
                    </button>
                    {errorMessage ? (
                      <p className="error-message festival-avatar-error-message">{errorMessage}</p>
                    ) : null}
                  </div>
                  <button
                    className="festival-avatar-next-button"
                    type="button"
                    onClick={handleGoToStoryboard}
                    disabled={!hasGeneratedCharacterPreview || isGlobalLoading}
                  >
                    <span>다음으로</span>
                    <span className="material-symbols-outlined">arrow_forward</span>
                  </button>
                </div>
              </section>
            </div>
          </section>

          {festivalFooter}
        </>
      ) : screen === 'storyboard' ? (
        <>
          <section className="hero-section storyboard-page">
            <div className="storyboard-shell storyboard-page-shell">
              <section
                className="storyboard-background-stage"
                ref={storyboardBackgroundSectionRef}
              >
                <div className="storyboard-background-stack">
                  <div className="storyboard-background-intro">
                    <h1 className="setup-title">배경 입력</h1>
                    <p className="setup-copy storyboard-background-copy">
                      주인공이 움직일 공간과 분위기를 먼저 설정한 뒤, 다음 단계에서 사건을 이어서 작성하세요.
                    </p>
                  </div>

                  <div className="festival-avatar-prompt-panel storyboard-background-prompt-panel">
                    <label className="festival-avatar-prompt-label" htmlFor="background">
                      배경 입력 (Prompt)
                    </label>
                    <div className="festival-avatar-prompt-shell">
                      <textarea
                        id="background"
                        ref={storyboardBackgroundPromptRef}
                        className="festival-avatar-prompt-input"
                        placeholder="예: 네온 간판이 빽빽한 미래도시 골목, 푸른 안개와 비가 흐르는 밤거리..."
                        aria-label="배경 프롬프트 입력"
                        value={background}
                        onChange={(eventObject) => handleBackgroundChange(eventObject.target.value)}
                        disabled={isGlobalLoading || isAnySceneCardLoading}
                      />
                    </div>
                  </div>

                  <div className="storyboard-background-actions">
                    <button
                      className="festival-avatar-next-button storyboard-scroll-button"
                      type="button"
                      onClick={handleScrollToEventPrompt}
                      disabled={!background.trim() || isGlobalLoading || isAnySceneCardLoading}
                    >
                      <span>다음으로</span>
                      <span className="material-symbols-outlined">arrow_downward</span>
                    </button>
                  </div>
                </div>
              </section>

              <section
                className="storyboard-background-stage storyboard-event-section"
                ref={storyboardEventSectionRef}
              >
                <div className="storyboard-background-stack">
                  <div className="storyboard-background-intro">
                    <h2 className="setup-title">사건 입력</h2>
                    <p className="setup-copy storyboard-background-copy">
                      주인공은 현재 어떤 상황에 놓여 있나요? 그리고 어떤 방식으로 문제를 해결하나요?
                    </p>
                  </div>

                  <div className="festival-avatar-prompt-panel storyboard-event-prompt-panel">
                    <label className="festival-avatar-prompt-label" htmlFor="event">
                      사건 입력 (Prompt)
                    </label>
                    <div className="festival-avatar-prompt-shell">
                      <textarea
                        id="event"
                        ref={storyboardEventPromptRef}
                        className="festival-avatar-prompt-input"
                        placeholder="예: 정체불명의 신호를 받은 주인공이 도시 전체가 멈춘 원인을 추적하기 시작한다..."
                        aria-label="사건 프롬프트 입력"
                        value={event}
                        onChange={(eventObject) => handleEventChange(eventObject.target.value)}
                        disabled={isGlobalLoading || isAnySceneCardLoading}
                      />
                    </div>
                  </div>

                  <div className="storyboard-compose-actions storyboard-event-actions">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={handleScrollToBackgroundPrompt}
                      disabled={isGlobalLoading || isAnySceneCardLoading}
                    >
                      이전으로
                    </button>
                    <button
                      className="hero-button setup-button"
                      type="button"
                      onClick={handleGenerateStoryboard}
                      disabled={!background.trim() || !event.trim() || isGlobalLoading || isAnySceneCardLoading}
                    >
                      {storyboard ? '스토리보드 다시 생성하기' : '스토리보드 생성'}
                    </button>
                  </div>
                </div>
              </section>

              {storyboard ? (
                <>
                  <div className="storyboard-result-heading" ref={storyboardResultSectionRef}>
                    <h2 className="storyboard-section-title storyboard-result-simple-title">
                      스토리보드
                    </h2>
                    <p className="storyboard-section-copy storyboard-result-simple-copy">
                      앞에 입력된 정보를 기반으로 스토리보드가 완성되었습니다.
                    </p>
                  </div>

                  {activeStoryboardScene ? (
                    <div className="storyboard-carousel storyboard-result-carousel">
                      <div className="storyboard-result-stage">
                        <article
                          className="scene-card scene-card-animate storyboard-carousel-card storyboard-result-card"
                          key={`${activeStoryboardScene.title}-${activeStoryboardSceneNumber}`}
                        >
                          <div className="storyboard-result-card-top">
                            <p className="scene-index">SCENE {activeStoryboardSceneNumber}</p>
                          </div>

                          <div className="storyboard-result-card-grid">
                            <div className="storyboard-result-card-copy-column">
                              <h2 className="scene-title">{activeStoryboardScene.title}</h2>
                              <p className="scene-summary">{activeStoryboardScene.summary}</p>
                              <div className="scene-visual storyboard-result-visual">
                                <span className="scene-visual-label">비주얼 가이드</span>
                                <p>{activeStoryboardScene.visual}</p>
                              </div>
                            </div>

                            <div className="storyboard-result-card-preview-column">
                              {activeGeneratedScene ? (
                                <div className="scene-card-preview storyboard-result-preview">
                                  <div className="storyboard-result-preview-head">
                                    <p className="storyboard-result-preview-label">장면생성결과</p>
                                    <button
                                      className="storyboard-result-preview-expand"
                                      type="button"
                                      aria-label={`${activeStoryboardScene.title} 장면 이미지 확대 보기`}
                                      onClick={() => handleOpenExpandedScenePreview({
                                        ...activeGeneratedScene,
                                        title: activeStoryboardScene.title,
                                      })}
                                    >
                                      <span className="material-symbols-outlined">zoom_in</span>
                                    </button>
                                  </div>
                                  <div className="scene-shot-frame storyboard-result-shot-frame">
                                    <img
                                      className="scene-shot-image"
                                      src={resolveAssetUrl(activeGeneratedScene.image_url)}
                                      alt={`${activeStoryboardScene.title} 장면 이미지`}
                                    />
                                  </div>
                                </div>
                              ) : (
                                <div className="storyboard-result-preview-placeholder">
                                  <h3 className="storyboard-result-preview-title">
                                    아직 장면 이미지가 없습니다.
                                  </h3>
                                  <p className="storyboard-result-preview-copy">
                                    이 장면 생성하기를 누르면 현재 장면의 구성과 주인공 참조 이미지를
                                    이용해 결과 프레임을 이 영역에 표시합니다.
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="scene-card-actions storyboard-result-card-actions">
                            <button
                              className="hero-button scene-card-button"
                              type="button"
                              onClick={() => handleGenerateSceneImages(activeStoryboardSceneNumber)}
                              disabled={!selectedReferenceCharacter || isGlobalLoading || isActiveStoryboardSceneLoading}
                            >
                              {isActiveStoryboardSceneLoading
                                ? '장면 생성 중...'
                                : activeGeneratedScene
                                  ? '장면 다시 생성하기'
                                  : '이 장면 생성하기'}
                            </button>
                          </div>

                          {isActiveStoryboardSceneLoading ? (
                            <div
                              className="scene-card-loading-overlay"
                              role="status"
                              aria-live="polite"
                              aria-busy="true"
                            >
                              <div className="scene-card-loading-shell">
                                {renderLoadingSpinner({ className: 'loading-spinner-compact' })}
                                <p className="scene-card-loading-text">이 장면을 생성하고 있어요</p>
                              </div>
                            </div>
                          ) : null}
                        </article>
                      </div>

                      <div className="storyboard-carousel-controls storyboard-result-controls">
                        <button
                          className="storyboard-carousel-button"
                          type="button"
                          onClick={() => setActiveStoryboardSceneIndex((currentIndex) => currentIndex - 1)}
                          disabled={activeStoryboardSceneIndex === 0}
                          aria-label="이전 장면 카드 보기"
                        >
                          <span className="material-symbols-outlined">chevron_left</span>
                        </button>
                        <span className="storyboard-carousel-count">
                          {activeStoryboardSceneNumber} / {storyboardScenes.length}
                        </span>
                        <button
                          className="storyboard-carousel-button"
                          type="button"
                          onClick={() => setActiveStoryboardSceneIndex((currentIndex) => currentIndex + 1)}
                          disabled={activeStoryboardSceneIndex === storyboardScenes.length - 1}
                          aria-label="다음 장면 카드 보기"
                        >
                          <span className="material-symbols-outlined">chevron_right</span>
                        </button>
                      </div>
                    </div>
                  ) : null}

                  <div className="storyboard-final-video-cta">
                    <p className="storyboard-final-video-note">
                      {hasAllStoryboardSceneImages
                        ? '6개의 장면 이미지가 모두 준비되었습니다. 이제 영상을 생성할 수 있습니다.'
                        : `영상 생성은 6개의 장면 이미지가 모두 준비된 뒤 가능합니다. (${generatedStoryboardSceneCount}/6)`}
                    </p>
                    <div className="setup-actions storyboard-final-video-actions">
                      <button
                        className="hero-button setup-button storyboard-final-video-button"
                        type="button"
                        onClick={() => handleGenerateFinalVideo()}
                        disabled={!hasAllStoryboardSceneImages || isGlobalLoading || isAnySceneCardLoading}
                      >
                        {loadingMode === 'final-video'
                          ? '영상 생성 중...'
                          : finalVideo
                            ? '영상 다시 생성하기'
                            : '영상 생성하기'}
                      </button>
                    </div>
                  </div>

                </>
              ) : null}

              {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
            </div>
          </section>

          {festivalFooter}
        </>
      ) : screen === 'character-design' ? (
        <section className="hero-section character-design-screen">
          <div className="storyboard-shell character-design-shell">
            <div className="storyboard-header character-design-header">
              <div className="character-design-header-top">
                <div>
                  <p className="setup-step">CHARACTER DESIGN</p>
                  <h1 className="setup-title character-design-title">주인공 캐릭터 시안 페이지</h1>
                  <p className="setup-copy character-design-copy">
                    Qwen3.5가 생성된 스토리보드를 읽고 주인공 외형을 스스로 추론한 뒤 영문 이미지
                    프롬프트를 만들고, Z-Image Turbo가 일본 애니메이션 주인공 스타일의 디자인
                    시안 3개를 생성합니다.
                  </p>
                </div>

                <div className="landing-header-actions">
                  <span className="landing-status-inline character-design-status-pill">
                    <span className="landing-status-pulse" />
                    {selectedCharacterOption ? 'REFERENCE SELECTED' : 'DESIGN OPTIONS'}
                  </span>
                </div>
              </div>

              <div className="storyboard-meta character-design-meta">
                <span className="storyboard-tag">프롬프트: Qwen3.5</span>
                <span className="storyboard-tag">이미지 생성: Z-Image Turbo</span>
                <span className="storyboard-tag">스타일: 일본 애니메이션 주인공</span>
                <span className="storyboard-tag">시안 수: 3개</span>
                {selectedCharacterOption ? (
                  <span className="storyboard-tag">
                    선택됨: {selectedCharacterOption.label}
                  </span>
                ) : null}
              </div>
            </div>

            <section className="storyboard-design-panel character-design-panel">
              <div className="character-design-panel-head">
                <div>
                  <p className="character-studio-label">DESIGN OPTIONS</p>
                  <h2 className="storyboard-section-title character-design-section-title">
                    스토리보드 기반 자동 외형 시안
                  </h2>
                </div>

                <div className="setup-actions character-design-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => setScreen('storyboard')}
                  >
                    스토리보드 페이지로
                  </button>
                  <button
                    className="hero-button setup-button"
                    type="button"
                    onClick={handleGenerateCharacterDesigns}
                    disabled={isGlobalLoading || isAnySceneCardLoading}
                  >
                    {characterDesigns ? '주인공 시안 다시 생성하기' : '주인공 시안 3개 생성하기'}
                  </button>
                </div>
              </div>

              {characterDesigns ? (
                <>
                  <p className="design-summary-banner character-design-summary-banner">
                    {characterDesigns.character_summary}
                  </p>

                  <div className="design-grid storyboard-design-grid character-design-grid">
                    {characterDesigns.options.map((option) => (
                      <button
                        key={option.option_id}
                        className={`design-card character-design-card${selectedCharacterOptionId === option.option_id
                          ? ' design-card-selected'
                          : ''
                          }`}
                        type="button"
                        aria-pressed={selectedCharacterOptionId === option.option_id}
                        onClick={() => handleSelectCharacterOption(option.option_id)}
                      >
                        <div className="design-image-frame">
                          <img
                            className="design-image"
                            src={resolveAssetUrl(option.image_url)}
                            alt={`${option.label} 주인공 캐릭터 시안`}
                          />
                        </div>
                        <div className="design-body">
                          <div className="character-design-card-head">
                            <p className="scene-index">{option.label}</p>
                            <span className="character-design-card-status">
                              {selectedCharacterOptionId === option.option_id ? 'SELECTED' : 'PREVIEW'}
                            </span>
                          </div>
                          <p className="design-summary">{option.summary}</p>
                          <span className="design-select-text">
                            {selectedCharacterOptionId === option.option_id
                              ? '선택된 시안'
                              : '이 시안 선택하기'}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>

                  <div className="setup-actions">
                    <button
                      className="hero-button setup-button"
                      type="button"
                      onClick={handleOpenSceneImagesPage}
                      disabled={!selectedReferenceCharacter}
                    >
                      장면 이미지 페이지로 이동
                    </button>
                  </div>
                </>
              ) : (
                <div className="design-empty-state character-design-empty-state">
                  <p>
                    아직 주인공 이미지가 생성되지 않았습니다. 이 페이지에서 버튼을 누르면
                    스토리보드를 바탕으로 AI가 외형을 추론한 일본 애니메이션 주인공 스타일
                    시안 3개가 생성됩니다.
                  </p>
                </div>
              )}
            </section>

            {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
          </div>
        </section>
      ) : screen === 'scene-images' ? (
        <section className="hero-section">
          <div className="storyboard-shell">
            <section className="storyboard-design-panel">
              <div className="setup-actions">

              </div>

              {sceneImages ? (
                <div className="scene-image-grid">
                </div>
              ) : (
                <div className="design-empty-state">
                  <p>
                    아직 장면 이미지가 생성되지 않았습니다. 캐릭터 시안을 하나 고른 뒤 버튼을
                    누르면 각 장면이 카드 형태로 생성됩니다.
                  </p>
                </div>
              )}
            </section>

            {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
          </div>
        </section>
      ) : screen === 'final-video' ? (
        <>
          <section className="hero-section storyboard-page">
            <div className="storyboard-shell">
              <div className="storyboard-header final-video-header">
                <h1 className="setup-title">완성된 애니메이션</h1>
              </div>

              <section className="storyboard-design-panel final-video-panel">
                {finalVideo?.video_url ? (
                  <div className="video-preview-panel">
                    <div className="final-video-frame">
                      <video
                        className="final-video-player"
                        controls
                        preload="metadata"
                        src={resolveAssetUrl(finalVideo.video_url)}
                        poster={sceneImages?.[0] ? resolveAssetUrl(sceneImages[0].image_url) : undefined}
                      />
                    </div>

                    <div className="setup-actions final-video-download-actions">
                      <button
                        className="hero-button setup-button final-video-download-button"
                        type="button"
                        onClick={handleOpenDownloadQrModal}
                      >
                        다운로드
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="design-empty-state">
                    <p>
                      아직 최종 영상이 생성되지 않았습니다. 장면 이미지가 준비된 뒤 최종 영상
                      만들기를 실행하면 완성본이 여기에 표시됩니다.
                    </p>
                  </div>
                )}
              </section>

              {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
            </div>
          </section>

          {festivalFooter}
        </>
      ) : null}

      {isGlobalLoading && !isCharacterImageLoading ? (
        <div className="loading-overlay" role="status" aria-live="polite" aria-busy="true">
          <div className="loading-card">
            {renderLoadingSpinner()}

            <p className="loading-eyebrow">{loadingContent.eyebrow}</p>
            <h2 className="loading-title">{loadingContent.title}</h2>
            <p className="loading-copy">{loadingContent.copy}</p>

            <div className="loading-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      ) : null}

      {expandedAvatarPreview ? (
        <div
          className="festival-avatar-preview-modal"
          role="dialog"
          aria-modal="true"
          aria-label="주인공 이미지 확대 보기"
          onClick={handleCloseExpandedAvatarPreview}
        >
          <div
            className="festival-avatar-preview-modal-dialog"
            onClick={(eventObject) => {
              eventObject.stopPropagation()
            }}
          >
            <div className="festival-avatar-preview-modal-image-frame">
              <button
                className="festival-avatar-preview-modal-close"
                type="button"
                aria-label="확대 이미지 닫기"
                onClick={handleCloseExpandedAvatarPreview}
              >
                <span className="material-symbols-outlined">close</span>
              </button>
              <img
                className="festival-avatar-preview-modal-image"
                src={resolveAssetUrl(expandedAvatarPreview.candidate.image_url)}
                alt={`생성된 주인공 후보 ${expandedAvatarPreview.index + 1} 확대 이미지`}
              />
            </div>
          </div>
        </div>
      ) : null}

      {expandedScenePreview ? (
        <div
          className="festival-avatar-preview-modal"
          role="dialog"
          aria-modal="true"
          aria-label="생성된 장면 이미지 확대 보기"
          onClick={handleCloseExpandedScenePreview}
        >
          <div
            className="festival-avatar-preview-modal-dialog"
            onClick={(eventObject) => {
              eventObject.stopPropagation()
            }}
          >
            <div className="festival-avatar-preview-modal-image-frame">
              <button
                className="festival-avatar-preview-modal-close"
                type="button"
                aria-label="확대 이미지 닫기"
                onClick={handleCloseExpandedScenePreview}
              >
                <span className="material-symbols-outlined">close</span>
              </button>
              <img
                className="festival-avatar-preview-modal-image"
                src={resolveAssetUrl(expandedScenePreview.image_url)}
                alt={`SCENE ${expandedScenePreview.scene_index} ${expandedScenePreview.title} 확대 이미지`}
              />
            </div>
          </div>
        </div>
      ) : null}

      {isDownloadQrModalOpen ? (
        <div
          className="festival-avatar-preview-modal"
          role="dialog"
          aria-modal="true"
          aria-label="완성 영상 다운로드 QR 코드"
          onClick={handleCloseDownloadQrModal}
        >
          <div
            className="festival-avatar-preview-modal-dialog download-qr-modal-dialog"
            onClick={(eventObject) => {
              eventObject.stopPropagation()
            }}
          >
            <div className="download-qr-modal-card">
              <button
                className="festival-avatar-preview-modal-close"
                type="button"
                aria-label="다운로드 QR 모달 닫기"
                onClick={handleCloseDownloadQrModal}
              >
                <span className="material-symbols-outlined">close</span>
              </button>

              <p className="setup-step download-qr-modal-step">DOWNLOAD</p>
              <h2 className="download-qr-modal-title">완성 영상 다운로드</h2>
              <p className="download-qr-modal-copy">
                아래 QR 코드를 스캔하면 완성된 영상을 다운로드할 수 있습니다.
              </p>

              <div className="download-qr-modal-code-shell">
                {downloadQrCodeDataUrl ? (
                  <img
                    className="download-qr-modal-image"
                    src={downloadQrCodeDataUrl}
                    alt="완성 영상 다운로드 QR 코드"
                  />
                ) : downloadQrCodeError ? (
                  <p className="download-qr-modal-error">{downloadQrCodeError}</p>
                ) : (
                  <div className="download-qr-modal-loading">
                    {renderLoadingSpinner({ className: 'loading-spinner-compact' })}
                    <p className="scene-card-loading-text">QR 코드를 생성하고 있어요</p>
                  </div>
                )}
              </div>

              <a className="hero-button download-qr-modal-link" href={finalVideoDownloadUrl}>
                직접 다운로드
              </a>

              <p className="download-qr-modal-hint">
                QR 코드는 다운로드 전용 주소를 사용합니다.
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  )
}

export default App
