import { Link } from "react-router-dom";
import { EmptyState, buttonClass } from "../components/ui.jsx";

export default function NotFoundPage() {
  return (
    <EmptyState
      title="Page not found"
      action={
        <Link to="/" className={buttonClass.primary}>
          Go to the dashboard
        </Link>
      }
    >
      This address does not match any page in the application.
    </EmptyState>
  );
}
