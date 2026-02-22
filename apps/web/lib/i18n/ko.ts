export const ko = {
  common: {
    save: "저장",
    cancel: "취소",
    delete: "삭제",
    edit: "수정",
    create: "생성",
    confirm: "확인",
    back: "돌아가기",
    next: "다음",
    prev: "이전",
    loading: "로딩 중...",
    noData: "데이터가 없습니다.",
    error: "오류가 발생했습니다.",
    success: "성공",
    search: "검색",
  },
  auth: {
    login: "로그인",
    logout: "로그아웃",
    signUp: "회원가입",
    email: "이메일",
    password: "비밀번호",
  },
  nav: {
    dashboard: "대시보드",
    requests: "요청 관리",
    users: "사용자 관리",
    organizations: "기관 관리",
    services: "서비스 관리",
    settings: "설정",
    apiKeys: "API 키",
    auditLogs: "감사 로그",
    reviews: "리뷰",
    newRequest: "새 요청",
    notifications: "알림",
    serviceCatalog: "서비스 카탈로그",
    myRequests: "내 요청",
    reviewQueue: "리뷰 대기",
  },
  sidebar: {
    home: "NeuroHub 홈으로 이동",
    mainNav: "메인 내비게이션",
    pageNav: "페이지 내비게이션",
    logout: "로그아웃",
    user: "사용자",
    switchToEn: "Switch to English",
    switchToKo: "한국어로 전환",
  },
  notification: {
    title: "알림",
    markAllRead: "모두 읽음",
    empty: "알림이 없습니다",
    unreadCount: "알림 {count}개 읽지 않음",
    markAllReadLabel: "모든 알림을 읽음으로 표시",
    list: "알림 목록",
  },
  expert: {
    pendingApproval: "관리자 승인 대기 중입니다. 승인 후 리뷰 기능을 사용할 수 있습니다.",
  },
  status: {
    CREATED: "생성됨",
    RECEIVING: "수신 중",
    STAGING: "준비 중",
    READY_TO_COMPUTE: "분석 대기",
    COMPUTING: "분석 중",
    QC: "품질 검증",
    REPORTING: "보고서 생성",
    EXPERT_REVIEW: "전문가 검토",
    FINAL: "완료",
    FAILED: "실패",
    CANCELLED: "취소",
  },
  userType: {
    SERVICE_USER: "서비스 사용자",
    EXPERT: "전문가 리뷰어",
    ADMIN: "관리자",
  },
} as const;

/** Structural type: same shape as `ko` but all leaf values are `string` */
type DeepStringify<T> = {
  [K in keyof T]: T[K] extends Record<string, unknown> ? DeepStringify<T[K]> : string;
};

export type TranslationKeys = DeepStringify<typeof ko>;
