const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const testResponses = {
  test1: {
    answer:
      "test1에 대한 테스트 답변입니다. 이 답변은 참고 공지사항 floating panel 동작을 확인하기 위한 임시 데이터입니다.",
    references: [
      {
        title: "테스트 공지사항 1",
        content: "test1 답변에서 참고한 첫 번째 테스트용 공지사항입니다.",
        date: "2026.05.24",
        url: "https://www.kookmin.ac.kr/user/kmuNews/notice/index.do",
      },
      {
        title: "테스트 공지사항 1-2",
        content: "test1 답변에서 참고한 두 번째 테스트용 공지사항입니다.",
        date: "2026.05.24",
        url: "https://www.kookmin.ac.kr/user/kmuNews/notice/index.do",
      },
    ],
  },

  test2: {
    answer:
      "test2에 대한 테스트 답변입니다. 관련 공지 확인하기 버튼을 누르면 이 답변에 연결된 참고 공지만 표시됩니다.",
    references: [
      {
        title: "테스트 공지사항 2",
        content: "test2 답변에서 참고한 테스트용 공지사항입니다.",
        date: "2026.05.24",
        url: "https://www.kookmin.ac.kr/user/kmuNews/notice/index.do",
      },
    ],
  },

  test3: {
    answer:
      "test3에 대한 테스트 답변입니다. 오른쪽 참고 공지사항 패널의 애니메이션과 링크 버튼을 확인할 수 있습니다.",
    references: [
      {
        title: "테스트 공지사항 3",
        content: "test3 답변에서 참고한 첫 번째 테스트용 공지사항입니다.",
        date: "2026.05.24",
        url: "https://www.kookmin.ac.kr/user/kmuNews/notice/index.do",
      },
      {
        title: "테스트 공지사항 3-2",
        content: "test3 답변에서 참고한 두 번째 테스트용 공지사항입니다.",
        date: "2026.05.24",
        url: "https://www.kookmin.ac.kr/user/kmuNews/notice/index.do",
      },
      {
        title: "테스트 공지사항 3-3",
        content: "test3 답변에서 참고한 세 번째 테스트용 공지사항입니다.",
        date: "2026.05.24",
        url: "https://www.kookmin.ac.kr/user/kmuNews/notice/index.do",
      },
    ],
  },
};

function getTestResponse(question) {
  const key = question.trim().toLowerCase();
  return testResponses[key] || null;
}

export async function sendChatMessage(question) {
  const testResponse = getTestResponse(question);

  if (testResponse) {
    await new Promise((resolve) => setTimeout(resolve, 450));
    return testResponse;
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error("채팅 API 요청에 실패했습니다.");
  }

  return response.json();
}