import Link from "next/link";
import { Button } from "@/shared/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen grid place-content-center gap-6 text-center p-6">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold">Página não encontrada</h2>
        <p className="text-muted-foreground">O conteúdo solicitado não está disponível ou foi movido.</p>
      </div>
      <Button asChild>
        <Link href="/">Voltar ao dashboard</Link>
      </Button>
    </div>
  );
}
