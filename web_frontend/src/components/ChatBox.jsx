import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

export default function ChatBox() {
  const {
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
  } = useChat();

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [deleteTargetSession, setDeleteTargetSession] = useState(null);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);

  const messageRefs = useRef({});
  const messageListRef = useRef(null);

  const checkScrollPosition = () => {
    const container = messageListRef.current;
    if (!container) return;

    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;

    setShowScrollToBottom(distanceFromBottom > 180);
  };

  const scrollToBottom = () => {
    const container = messageListRef.current;
    if (!container) return;

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });

    setShowScrollToBottom(false);
  };

  const closeSidebar = () => {
    setEditingSessionId(null);
    setEditingTitle("");
    setIsSidebarOpen(false);
  };

  const handleReferenceClick = (messageId) => {
    openReferencesForMessage(messageId);

    const target = messageRefs.current[messageId];
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  };

  const beginEdit = (event, session) => {
    event.stopPropagation();
    setEditingSessionId(session.id);
    setEditingTitle(session.title);
  };

  const submitEdit = (event, sessionId) => {
    event.preventDefault();
    event.stopPropagation();

    renameSession(sessionId, editingTitle);
    setEditingSessionId(null);
    setEditingTitle("");
  };

  const cancelEdit = () => {
    setEditingSessionId(null);
    setEditingTitle("");
  };

  const openDeleteModal = (event, session) => {
    event.stopPropagation();
    cancelEdit();
    setDeleteTargetSession(session);
  };

  const confirmDelete = () => {
    if (!deleteTargetSession) return;

    deleteSession(deleteTargetSession.id);
    setDeleteTargetSession(null);
    cancelEdit();
  };

  const cancelDelete = () => {
    setDeleteTargetSession(null);
  };

  useEffect(() => {
    if (!isSidebarOpen) {
      cancelEdit();
    }
  }, [isSidebarOpen]);

  useEffect(() => {
    const container = messageListRef.current;
    if (!container) return;

    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });

    requestAnimationFrame(checkScrollPosition);
  }, [messages.length, isLoading, currentSessionId]);

  return (
    <div className="app-shell">
      <div className={`intro-gradient ${hasConversation ? "hide" : ""}`} />
      <div
        className={`floating-chat-title ${isSidebarOpen ? "hidden" : ""} ${
          currentSession ? "" : "title-empty"
        }`}
      >
        <button
          className="floating-sidebar-toggle"
          onClick={() => setIsSidebarOpen(true)}
          aria-label="대화 기록 열기"
        >
          ☰
        </button>

        {currentSession && (
          <span title={currentSession.title}>
            {currentSession.title}
          </span>
        )}
      </div>
      

      <aside className={`history-sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="sidebar-title-row">
          <div className="sidebar-title-block">
            <h2>소융돌이</h2>
            <p>KMU Software Chatbot</p>
          </div>

          <button
            className="sidebar-collapse-button"
            onClick={closeSidebar}
            aria-label="대화 기록 닫기"
          >
            ←
          </button>
        </div>

        <button
          className="new-chat-button"
          onClick={() => {
            startNewChat();
            closeSidebar();
          }}
        >
          + 새 대화
        </button>

        <div className="history-list">
          {sessions.length > 0 ? (
            sessions.map((session) => (
              <div
                key={session.id}
                className={`history-item ${
                  currentSessionId === session.id ? "active" : ""
                }`}
                onClick={() => {
                  if (editingSessionId) {
                    cancelEdit();
                    return;
                  }

                  selectSession(session.id);
                  closeSidebar();
                }}
              >
                {editingSessionId === session.id ? (
                  <form
                    className="history-edit-form"
                    onSubmit={(event) => submitEdit(event, session.id)}
                    onClick={(event) => event.stopPropagation()}
                  >
                    <input
                      value={editingTitle}
                      autoFocus
                      onChange={(event) => setEditingTitle(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          cancelEdit();
                        }
                      }}
                    />
                    <button type="submit">저장</button>
                  </form>
                ) : (
                  <>
                    <div className="history-text">
                      <span title={session.title}>{session.title}</span>
                      <small>{session.time}</small>
                    </div>

                    <div className="history-actions">
                      <button
                        className="history-edit-button"
                        onClick={(event) => beginEdit(event, session)}
                        aria-label="대화명 수정"
                        title="대화명 수정"
                      >
                        ✎
                      </button>

                      <button
                        className="history-delete-button"
                        onClick={(event) => openDeleteModal(event, session)}
                        aria-label="대화 기록 삭제"
                        title="대화 기록 삭제"
                      >
                        🗑
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          ) : (
            <p className="empty-history">저장된 대화가 없습니다.</p>
          )}
        </div>
      </aside>

      <div
        className={`sidebar-backdrop ${isSidebarOpen ? "show" : ""}`}
        onClick={closeSidebar}
      />

      <main className="chat-stage">
        <section className="chat-panel">
          <div className={`empty-intro ${hasConversation ? "fade-out" : ""}`}>
            <p>국민대학교 소프트웨어융합대학 챗봇 소융돌이입니다.</p>
            <h1>무엇을 도와드릴까요?</h1>
            <span>
              소프트웨어융합대학 공지사항을 기반으로 답변합니다.
              <br />
              중요한 내용은 반드시 원문 공지를 확인하세요.
            </span>
          </div>

          <MessageList
            refContainer={messageListRef}
            messages={messages}
            isLoading={isLoading}
            activeReferenceMessageId={activeReferenceMessageId}
            messageRefs={messageRefs}
            onReferenceClick={handleReferenceClick}
            onScroll={checkScrollPosition}
          />

          {showScrollToBottom && (
            <button className="scroll-to-bottom-button" onClick={scrollToBottom}>
              <span>⬇</span>
            </button>
          )}

          <MessageInput onSend={sendMessage} isLoading={isLoading} />
        </section>
      </main>

      <aside className={`reference-floating ${isReferenceOpen ? "open" : ""}`}>
        <div className="reference-card-shell">
          <div className="reference-header">
            <div>
              <p>References</p>
              <h3>참고한 공지사항</h3>
            </div>

            <button onClick={closeReferences}>×</button>
          </div>

          {activeReferences.length > 0 ? (
            <div className="reference-list">
              {activeReferences.map((ref, index) => {
                const href = ref.url || ref.link || ref.href || "";

                return (
                  <article className="reference-item" key={`${ref.title}-${index}`}>
                    <div className="reference-number">{index + 1}</div>

                    <div className="reference-content">
                      <h4>{ref.title || "공지 제목 없음"}</h4>

                      {ref.date && (
                        <span className="reference-date">{ref.date}</span>
                      )}

                      {ref.content && <p>{ref.content}</p>}

                      {href ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          className="notice-link"
                        >
                          공지 보러가기
                        </a>
                      ) : (
                        <button className="notice-link disabled" disabled>
                          링크 없음
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="empty-reference">
              이 답변에 연결된 참고 공지가 없습니다.
            </div>
          )}
        </div>
      </aside>

      {deleteTargetSession && (
        <div className="modal-backdrop" onClick={cancelDelete}>
          <div
            className="delete-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="delete-modal-icon">!</div>

            <h3>대화 기록 삭제</h3>

            <p>
              <strong>{deleteTargetSession.title}</strong> 기록을 삭제하겠습니까?
              <br />
              삭제한 대화는 로컬 캐시에서 제거됩니다.
            </p>

            <div className="delete-modal-actions">
              <button className="cancel-delete-button" onClick={cancelDelete}>
                취소
              </button>

              <button className="confirm-delete-button" onClick={confirmDelete}>
                삭제하기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}