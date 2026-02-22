import Link from "next/link";

export default function NotFound() {
  return (
    <div className="auth-page">
      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: 72, fontWeight: 800, color: "var(--muted)", margin: "0 0 8px", opacity: 0.3 }}>
          404
        </p>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>
          페이지를 찾을 수 없습니다
        </h1>
        <p className="muted-text" style={{ marginBottom: 24 }}>
          요청하신 페이지가 존재하지 않거나 이동되었습니다.
        </p>
        <Link href="/" className="btn btn-primary" style={{ display: "inline-flex" }}>
          홈으로 돌아가기
        </Link>
      </div>
    </div>
  );
}
