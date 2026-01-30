function createChart(elementId, title, labels, data) {
    const ctx = document.getElementById(elementId);
    if (ctx) {
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(153, 102, 255, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: title,
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
    }
}

document.addEventListener('alpine:init', () => {
    // Initialize stores first
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

    // Then initialize component
    Alpine.data('state', () => ({
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
    }));

    // Initialize state as a store
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

    // Update the component to reference the store
    Alpine.data('state', () => ({
        startDate: Alpine.store('state').startDate,
        endDate: Alpine.store('state').endDate
    }));

    Alpine.effect(() => {
        const state = Alpine.store('state');
        createChart(
            'incomeChart', 
            `Income: $${state.incomeData.sum.toFixed(2)}`, 
            state.incomeData.labels, 
            state.incomeData.data
        );
        
        createChart(
            'expenseChart', 
            `Expense: $${state.expenseData.sum.toFixed(2)}`, 
            state.expenseData.labels, 
            state.expenseData.data
        );
    });
});
