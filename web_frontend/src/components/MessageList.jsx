export default function MessageList({
  refContainer,
  messages,
  isLoading,
  activeReferenceMessageId,
  messageRefs,
  onReferenceClick,
}) {
  return (
    <div className="message-list" ref={refContainer}>
      {messages.map((message) => (
        <article
          key={message.id}
          ref={(element) => {
            if (element) {
              messageRefs.current[message.id] = element;
            }
          }}
          className={`message-row ${
            message.role === "user" ? "user-message" : "assistant-message"
          } ${
            activeReferenceMessageId === message.id ? "reference-focused" : ""
          }`}
        >
          <div className="message-meta">
            <strong>{message.role === "user" ? "나" : "챗봇"}</strong>
            <span>{message.time}</span>
          </div>

          <div className="message-bubble">
            <p>{message.content}</p>

            {message.role === "assistant" && message.references?.length > 0 && (
              <button
                className="reference-check-button"
                onClick={() => onReferenceClick(message.id)}
              >
                관련 공지 확인하기
              </button>
            )}
          </div>
        </article>
      ))}

      {isLoading && (
        <article className="message-row assistant-message">
          <div className="message-meta">
            <strong>챗봇</strong>
            <span>응답 생성 중</span>
          </div>

          <div className="message-bubble loading-bubble">
            <span />
            <span />
            <span />
          </div>
        </article>
      )}
    </div>
  );
}