import { useEffect, useMemo, useRef, useState } from "react";
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

function createSessionWithFirstMessage(sessions, firstMessage) {
  const content = firstMessage.content;
  const title = content.length > 10 ? content.slice(0, 10) + "..." : content;

  return {
    id: createId(),
    title,
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
  const [loadingSessionId, setLoadingSessionId] = useState(null);
  const referenceCloseTimerRef = useRef(null);

  const currentSession = useMemo(() => {
    if (!currentSessionId) return null;
    return sessions.find((session) => session.id === currentSessionId) || null;
  }, [sessions, currentSessionId]);

  const messages = currentSession?.messages || [];
  const hasConversation = messages.length > 0;
  const isCurrentSessionLoading = Boolean(currentSessionId) && loadingSessionId === currentSessionId;

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
    if (referenceCloseTimerRef.current) {
      clearTimeout(referenceCloseTimerRef.current);
      referenceCloseTimerRef.current = null;
    }

    setIsReferenceOpen(false);
    setActiveReferenceMessageId(null);
    setActiveReferences([]);
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
    if (!trimmed) return;

    if (currentSessionId && loadingSessionId === currentSessionId) {
      return;
    }

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

    setLoadingSessionId(targetSessionId);

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
      setLoadingSessionId((prev) => {
        if (prev === targetSessionId) return null;
        return prev;
      });
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

    if (referenceCloseTimerRef.current) {
      clearTimeout(referenceCloseTimerRef.current);
      referenceCloseTimerRef.current = null;
    }

    setActiveReferenceMessageId(messageId);
    setActiveReferences(target.references || []);
    setIsReferenceOpen(true);
  };

  const closeReferences = () => {
    setIsReferenceOpen(false);

    if (referenceCloseTimerRef.current) {
      clearTimeout(referenceCloseTimerRef.current);
    }

    referenceCloseTimerRef.current = setTimeout(() => {
      setActiveReferenceMessageId(null);
      setActiveReferences([]);
      referenceCloseTimerRef.current = null;
    }, 340);
  };

  return {
    sessions,
    currentSession,
    currentSessionId,
    messages,
    activeReferenceMessageId,
    activeReferences,
    isReferenceOpen,
    isLoading: isCurrentSessionLoading,
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