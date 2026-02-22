"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Spinner, CheckCircle, XCircle, PlusCircle } from "phosphor-react";
import { listRequests } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MetricCard } from "@/components/metric-card";
import { RequestCard } from "@/components/request-card";

export default function UserDashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const { data } = useQuery({ queryKey: ["requests"], queryFn: listRequests });

  const requests = data?.items ?? [];
  const inProgress = requests.filter((r) => !["FINAL", "FAILED", "CANCELLED"].includes(r.status)).length;
  const completed = requests.filter((r) => r.status === "FINAL").length;
  const failed = requests.filter((r) => r.status === "FAILED").length;
  const recent = requests.slice(0, 5);

  return (
    <div className="stack-lg">
      <div>
        <h1 className="greeting">안녕하세요, {user?.displayName || "사용자"}님</h1>
        <p className="greeting-sub">의료 AI 분석 현황을 확인하세요</p>
      </div>

      <div className="grid-3">
        <MetricCard
          icon={<Spinner size={20} />}
          label="진행 중"
          value={inProgress}
          iconBg="var(--primary-light)"
          iconColor="var(--primary)"
        />
        <MetricCard
          icon={<CheckCircle size={20} />}
          label="완료"
          value={completed}
          iconBg="var(--success-light)"
          iconColor="var(--success)"
        />
        <MetricCard
          icon={<XCircle size={20} />}
          label="실패"
          value={failed}
          iconBg="var(--danger-light)"
          iconColor="var(--danger)"
        />
      </div>

      <div className="cta-card" onClick={() => router.push("/user/new-request")}>
        <div className="cta-card-icon"><PlusCircle size={32} /></div>
        <p className="cta-card-title">새 요청 만들기</p>
        <p className="cta-card-desc">의료 데이터를 제출하고 AI 분석을 시작하세요</p>
      </div>

      <div className="panel">
        <div className="panel-header-row" style={{ marginBottom: 16 }}>
          <h2 className="panel-title">최근 요청</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => router.push("/user/requests")}>
            전체 보기
          </button>
        </div>
        {recent.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state-text">아직 요청이 없습니다. 새 요청을 만들어보세요.</p>
          </div>
        ) : (
          <div className="stack-md">
            {recent.map((req) => (
              <RequestCard key={req.id} request={req} onClick={() => router.push(`/user/requests/${req.id}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
