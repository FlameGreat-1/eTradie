import { Link } from 'react-router-dom';
import RegisterForm from '@/features/auth/components/RegisterForm';

export default function RegisterPage() {
  return (
    <div className="flex flex-col items-center">
      <RegisterForm />
      <p className="mt-6 text-xs text-content-muted">
        Already have an account?{' '}
        <Link to="/login" className="text-brand hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
