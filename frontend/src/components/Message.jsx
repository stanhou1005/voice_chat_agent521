export default function Message({ role, text }) {
  return (
    <div className={`message message-${role}`}>
      <div className="message-bubble">
        <p>{text}</p>
      </div>
    </div>
  );
}
