// src/api/chatApi.js

const API_BASE_URL = "https://professor-especially-spokesman-package.trycloudflare.com"; // ngrok으로 생성된 URL로 변경

export async function sendChatMessage(question) {
  // 백엔드(FastAPI)가 요구하는 Request 양식에 맞춤
  const payload = {
    question: question,
    top_k: 3,
    candidate_k: 40
  };

  const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Bypass-Tunnel-Reminder": "true" // ngrok 터널을 사용할 때, ngrok이 요청을 차단하지 않도록 하는 헤더
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`채팅 API 요청에 실패했습니다. (상태 코드: ${response.status})`);
  }

  // 성공 시 { answer: string, references: array } 형태의 객체를 반환합니다.
  return response.json();
}