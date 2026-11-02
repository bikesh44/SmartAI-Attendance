import "./PageState.css";

function PageState({
  title,
  message,
  type = "info",
}) {
  return (
    <div className={`page-state page-state-${type}`}>
      <div className="page-state-icon">
        {type === "error" ? "!" : type === "loading" ? "..." : "i"}
      </div>

      <h2>{title}</h2>

      <p>{message}</p>
    </div>
  );
}

export default PageState;