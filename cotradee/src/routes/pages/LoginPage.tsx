import { Link } from 'react-router-dom';
import LoginForm from '@/features/auth/components/LoginForm';

export default function LoginPage() {
  return (
    <div className="flex flex-col items-center">
      <LoginForm />
      <p className="mt-6 text-xs text-content-muted">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="text-brand hover:underline font-medium">
          Create one
        </Link>
      </p>
    </div>
  );
}
