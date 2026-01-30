document.addEventListener('alpine:init', () => {
    Alpine.store('state', {
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        get incomeData() {
            const income = Alpine.store('notifications').transactions.filter(t => t.type === 'income');
            const sum = income.reduce((acc, t) => acc + t.amount, 0);
            const byCategory = {};
            
            income.forEach(t => {
                byCategory[t.category] = (byCategory[t.category] || 0) + t.amount;
            });
            
            return {
                labels: Object.keys(byCategory),
                data: Object.values(byCategory),
                sum: sum
            };
        },
        get expenseData() {
            const expense = Alpine.store('notifications').transactions.filter(t => t.type === 'expense');
            const sum = expense.reduce((acc, t) => acc + t.amount, 0);
            const byCategory = {};
            
            expense.forEach(t => {
                byCategory[t.category] = (byCategory[t.category] || 0) + t.amount;
            });
            
            return {
                labels: Object.keys(byCategory),
                data: Object.values(byCategory),
                sum: sum
            };
        }
    });
    Alpine.store('notifications', {
        transactions: [
            {
                account: 'main',
                category: 'salary',
                type: 'income',
                amount: 100000.00
            },
            {
                account: 'main',
                category: 'present',
                type: 'income',
                amount: 100000.00
            },
            {
                account: 'main',
                category: 'family',
                type: 'expense',
                amount: 50000.00
            },
            {
                account: 'main',
                category: 'family',
                type: 'expense',
                amount: 50000.00
            },
            {
                account: 'food',
                category: 'family',
                type: 'expense',
                amount: 500.00
            }
        ],
        incomeCategories: ['salary', 'present'],
        expenseCategories: ['food', 'family', 'transport'],
        accounts: ['main'],
    });
});
