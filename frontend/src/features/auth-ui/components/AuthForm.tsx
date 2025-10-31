"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoginInput, LoginSchema } from "@/entities/auth/schemas";
import { Input } from "@/shared/ui/input";
import { Button } from "@/shared/ui/button";

interface AuthFormProps {
  onSubmit: (data: LoginInput) => Promise<void> | void;
  isLoading?: boolean;
  error?: string | null;
}

export default function AuthForm({ onSubmit, isLoading, error }: AuthFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(LoginSchema),
  });

  const handle = async (data: LoginInput) => {
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit(handle)} className="space-y-3">
      <div className="space-y-1">
        <Input placeholder="email@exemplo.com" autoComplete="email" {...register("email")} />
        {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
      </div>

      <div className="space-y-1">
        <Input type="password" placeholder="••••••••" autoComplete="current-password" {...register("password")} />
        {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <Button type="submit" disabled={isSubmitting || isLoading} className="w-full">
        {isSubmitting || isLoading ? "Autenticando..." : "Entrar"}
      </Button>
    </form>
  );
}
