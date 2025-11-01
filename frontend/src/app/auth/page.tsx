

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthForm from "@/features/auth-ui/components/AuthForm";
import { login } from "@/shared/api/auth";
import { useAuth } from "@/shared/hooks/useAuth";
import type { LoginInput } from "@/entities/auth/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

export default function AuthPage() {
  const router = useRouter();
  const { isAuthenticated, isReady, applyLogin } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isReady && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, isReady, router]);

  const handleLogin = async (payload: LoginInput) => {
    try {
      setError(null);
      setIsLoading(true);
      const response = await login(payload);
      applyLogin(response);
      router.replace("/");
    } catch (err) {
      setError("Falha ao autenticar. Verifique suas credenciais.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isReady && isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen grid place-items-center bg-muted/40 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center text-xl">Entrar no RestaurantBI</CardTitle>
        </CardHeader>
        <CardContent>
          <AuthForm onSubmit={handleLogin} error={error} isLoading={isLoading} />
        </CardContent>
      </Card>
    </div>
  );
}
