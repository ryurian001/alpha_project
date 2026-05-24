import { useState } from "react";

export default function MessageInput({ onSend, isLoading }) {
  const [value, setValue] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    const trimmed = value.trim();
    if (!trimmed || isLoading) return;

    onSend(trimmed);
    setValue("");
  };

  return (
    <form className="message-input-form" onSubmit={handleSubmit}>
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="질문을 입력하세요"
        disabled={isLoading}
      />

      <button type="submit" disabled={isLoading || !value.trim()}>
        전송
      </button>
    </form>
  );
}