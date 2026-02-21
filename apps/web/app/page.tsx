import Link from "next/link";

export default function HomePage() {
  return (
    <section className="panel panel-hero">
      <div>
        <p className="hero-kicker">한국어 우선 인터페이스</p>
        <h2 className="hero-title">NeuroHub 초기 실행 환경이 준비되었습니다.</h2>
        <p className="hero-description">
          요청 생성, 상태 전이, 비동기 실행 파이프라인(Celery/Outbox) 기준으로 시작할 수 있습니다.
        </p>
      </div>
      <div className="hero-actions">
        <Link className="btn btn-primary" href="/dashboard">
          대시보드로 이동
        </Link>
        <Link className="btn btn-secondary" href="/new-request">
          첫 요청 만들기
        </Link>
      </div>
    </section>
  );
}
