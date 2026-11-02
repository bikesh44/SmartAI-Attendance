function StatCard({ title, value, description, className = "" }) {
  return (
    <article className={`stat-card ${className}`.trim()}>
      <div className="stat-card-header">
        <span className="stat-card-title">{title}</span>
      </div>

      <p className="stat-card-value">{value}</p>

      {description && (
        <p className="stat-card-description">{description}</p>
      )}
    </article>
  );
}

export default StatCard;
