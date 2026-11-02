import "./DataTable.css";
function DataTable({
  columns,
  data,
  emptyMessage = "No data available.",
}) {
  if (!data || data.length === 0) {
    return (
      <div className="data-table-empty">
        <div className="data-table-empty-icon">--</div>

        <strong>No records available</strong>

        <span>{emptyMessage}</span>
      </div>
    );
  }

  return (
    <div className="data-table-wrapper">
      <div className="data-table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} scope="col">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {data.map((row, index) => (
              <tr key={row.id ?? index}>
                {columns.map((column) => (
                  <td key={column.key}>
                    {row[column.key] ?? "--"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;