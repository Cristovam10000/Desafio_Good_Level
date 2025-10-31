import { Card } from "@/shared/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

type ProductRow = {
  id: number;
  product: string;
  revenue: number;
  orders: number;
  qty: number;
};

function formatCurrency(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatNumber(value: number) {
  return value.toLocaleString("pt-BR");
}

export default function AnalyticsTable({ rows }: { rows: ProductRow[] }) {
  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Ranking de produtos</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Produto</TableHead>
            <TableHead className="text-right">Receita</TableHead>
            <TableHead className="text-right">Pedidos</TableHead>
            <TableHead className="text-right">Quantidade</TableHead>
            <TableHead className="text-right">Ticket Médio</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-sm text-muted-foreground py-6">
                Nenhum produto disponível para o período selecionado.
              </TableCell>
            </TableRow>
          )}
          {rows.map((row) => {
            const ticket = row.orders > 0 ? row.revenue / row.orders : 0;
            return (
              <TableRow key={row.id}>
                <TableCell className="font-medium">{row.product}</TableCell>
                <TableCell className="text-right">{formatCurrency(row.revenue)}</TableCell>
                <TableCell className="text-right">{formatNumber(row.orders)}</TableCell>
                <TableCell className="text-right">{formatNumber(row.qty)}</TableCell>
                <TableCell className="text-right">{formatCurrency(ticket)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Card>
  );
}
