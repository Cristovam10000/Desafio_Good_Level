// Script para testar datas do dashboard
const { formatISO, subDays } = require('date-fns');

const today = new Date();
console.log('Hoje:', today.toISOString());

// Simular rangeForPreset("7days")
const start7 = formatISO(subDays(today, 6), { representation: 'date' });
const end7 = formatISO(today, { representation: 'date' });
console.log('\n7 dias (Dashboard padrão):');
console.log('  Start:', start7);
console.log('  End:', end7);

// Simular isoRangeForLastNDays(30) do Analytics
const start30 = formatISO(subDays(today, 30), { representation: 'date' });
const end30 = formatISO(today, { representation: 'date' });
console.log('\n30 dias (Analytics):');
console.log('  Start:', start30);
console.log('  End:', end30);

// Verificar se há overlap com dados do banco (2025-05-05 até 2025-11-01)
console.log('\n=== OVERLAP COM DADOS DO BANCO ===');
console.log('Dados no banco: 2025-05-05 até 2025-11-01');
console.log('Dashboard (7 dias):', start7, 'até', end7);
console.log('Analytics (30 dias):', start30, 'até', end30);

// O problema: se hoje é 01/nov, o range de 7 dias vai de 26/out até 01/nov
// mas o banco só tem dados ATÉ 01/nov 23:59
// Se a consulta for feita COM timezone ou arredondamento, pode não pegar nada!
