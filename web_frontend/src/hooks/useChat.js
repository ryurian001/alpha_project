import { useEffect, useMemo, useState } from "react";
import { sendChatMessage } from "../api/chatApi";

const SESSIONS_STORAGE_KEY = "kmu_chatbot_sessions";
const CURRENT_SESSION_KEY = "kmu_chatbot_current_session_id";

function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function saveToStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function getCurrentTime() {
  return new Date().toLocaleTimeString("ko-KR", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function getDateLabel() {
  return new Date().toLocaleDateString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
  });
}

function createId() {
  return crypto.randomUUID();
}

function getNextChatTitle(sessions) {
  const usedNumbers = new Set();

  sessions.forEach((session) => {
    const match = /^새 대화 (\d+)$/.exec(session.title);
    if (match) {
      usedNumbers.add(Number(match[1]));
    }
  });

  let next = 1;
  while (usedNumbers.has(next)) {
    next += 1;
  }

  return `새 대화 ${next}`;
}

function createSessionWithFirstMessage(sessions, firstMessage) {
  return {
    id: createId(),
    title: getNextChatTitle(sessions),
    messages: [firstMessage],
    createdAt: Date.now(),
    updatedAt: Date.now(),
    time: getDateLabel(),
  };
}

function normalizeInitialState() {
  const savedSessions = loadFromStorage(SESSIONS_STORAGE_KEY, []);
  const savedCurrentId = localStorage.getItem(CURRENT_SESSION_KEY);

  const validSessions = savedSessions.filter(
    (session) => Array.isArray(session.messages) && session.messages.length > 0
  );

  const currentExists = validSessions.some(
    (session) => session.id === savedCurrentId
  );

  return {
    sessions: validSessions,
    currentSessionId: currentExists ? savedCurrentId : null,
  };
}

export function useChat() {
  const initialState = useMemo(() => normalizeInitialState(), []);

  const [sessions, setSessions] = useState(initialState.sessions);
  const [currentSessionId, setCurrentSessionId] = useState(
    initialState.currentSessionId
  );

  const [activeReferenceMessageId, setActiveReferenceMessageId] = useState(null);
  const [activeReferences, setActiveReferences] = useState([]);
  const [isReferenceOpen, setIsReferenceOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const currentSession = useMemo(() => {
    if (!currentSessionId) return null;
    return sessions.find((session) => session.id === currentSessionId) || null;
  }, [sessions, currentSessionId]);

  const messages = currentSession?.messages || [];
  const hasConversation = messages.length > 0;

  useEffect(() => {
    const nonEmptySessions = sessions.filter(
      (session) => session.messages && session.messages.length > 0
    );

    saveToStorage(SESSIONS_STORAGE_KEY, nonEmptySessions);
  }, [sessions]);

  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem(CURRENT_SESSION_KEY, currentSessionId);
    } else {
      localStorage.removeItem(CURRENT_SESSION_KEY);
    }
  }, [currentSessionId]);

  const resetReferenceState = () => {
    setActiveReferenceMessageId(null);
    setActiveReferences([]);
    setIsReferenceOpen(false);
  };

  const appendMessageToSession = (sessionId, message) => {
    setSessions((prev) =>
      prev.map((session) => {
        if (session.id !== sessionId) return session;

        return {
          ...session,
          messages: [...session.messages, message],
          updatedAt: Date.now(),
          time: getDateLabel(),
        };
      })
    );
  };

  const sendMessage = async (question) => {
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    const userMessage = {
      id: createId(),
      role: "user",
      content: trimmed,
      time: getCurrentTime(),
    };

    let targetSessionId = currentSessionId;

    if (!targetSessionId) {
      const newSession = createSessionWithFirstMessage(sessions, userMessage);
      targetSessionId = newSession.id;

      setSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
    } else {
      appendMessageToSession(targetSessionId, userMessage);
    }

    setIsLoading(true);

    try {
      const result = await sendChatMessage(trimmed);

      const assistantMessage = {
        id: createId(),
        role: "assistant",
        content: result.answer || "답변을 생성하지 못했습니다.",
        references: Array.isArray(result.references) ? result.references : [],
        time: getCurrentTime(),
      };

      appendMessageToSession(targetSessionId, assistantMessage);
    } catch {
      const errorMessage = {
        id: createId(),
        role: "assistant",
        content:
          "현재 백엔드 서버와 연결되지 않았습니다. FastAPI 서버가 실행 중인지 확인해주세요.",
        references: [],
        time: getCurrentTime(),
      };

      appendMessageToSession(targetSessionId, errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = () => {
    setCurrentSessionId(null);
    resetReferenceState();
  };

  const selectSession = (sessionId) => {
    setCurrentSessionId(sessionId);
    resetReferenceState();
  };

  const renameSession = (sessionId, nextTitle) => {
    const trimmed = nextTitle.trim();
    if (!trimmed) return;

    setSessions((prev) =>
      prev.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              title: trimmed,
              updatedAt: Date.now(),
            }
          : session
      )
    );
  };

  const deleteSession = (sessionId) => {
    setSessions((prev) => prev.filter((session) => session.id !== sessionId));

    if (currentSessionId === sessionId) {
      setCurrentSessionId(null);
      resetReferenceState();
    }
  };

  const openReferencesForMessage = (messageId) => {
    const target = messages.find((message) => message.id === messageId);
    if (!target) return;

    setActiveReferenceMessageId(messageId);
    setActiveReferences(target.references || []);
    setIsReferenceOpen(true);
  };

  const closeReferences = () => {
    resetReferenceState();
  };

  return {
    sessions,
    currentSession,
    currentSessionId,
    messages,
    activeReferenceMessageId,
    activeReferences,
    isReferenceOpen,
    isLoading,
    hasConversation,
    sendMessage,
    startNewChat,
    selectSession,
    renameSession,
    deleteSession,
    openReferencesForMessage,
    closeReferences,
  };
}