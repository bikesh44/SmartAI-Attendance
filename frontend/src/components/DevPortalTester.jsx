import { useNavigate } from "react-router-dom";
import useAuth from "../hooks/useAuth";

function DevPortalTester() {
  const { setTestUser } = useAuth();
  const navigate = useNavigate();

  function loginAs(role, path) {
    setTestUser(role);
    navigate(path);
  }

  if (!import.meta.env.DEV) {
    return null;
  }

  return (
    <section>
      <h2>Development Portal Testing</h2>

      <p>
        These buttons are available only during frontend development.
      </p>

      <div>
        <button
          type="button"
          onClick={() => loginAs("ADMIN", "/admin")}
        >
          Test Admin Portal
        </button>

        <button
          type="button"
          onClick={() => loginAs("FACULTY", "/faculty")}
        >
          Test Faculty Portal
        </button>

        <button
          type="button"
          onClick={() => loginAs("STUDENT", "/student")}
        >
          Test Student Portal
        </button>
      </div>
    </section>
  );
}

export default DevPortalTester;