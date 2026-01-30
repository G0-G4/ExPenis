function createChart(elementId, title, labels, data) {
    const ctx = document.getElementById(elementId);
    if (ctx) {
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
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
    Alpine.store('store', {
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
                category: 'food',
                type: 'expense',
                amount: 50000.00
            },
            {
                account: 'main',
                category: 'transport',
                type: 'expense',
                amount: 1000.00
            }
        ],
        incomeCategories: ['salary', 'present'],
        expenseCategories: ['food', 'family', 'transport'],
        accounts: ['main'],
    });

    // Initialize component with data and chart logic
    Alpine.data('state', () => ({
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        init() {
            this.$watch('startDate', () => this.updateCharts());
            this.$watch('endDate', () => this.updateCharts());
            this.updateCharts();
        },
        get incomeData() {
            const income = Alpine.store('store').transactions.filter(t => t.type === 'income');
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
            const expense = Alpine.store('store').transactions.filter(t => t.type === 'expense');
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
        },
        updateCharts() {
            createChart(
                'incomeChart', 
                `Income: $${this.incomeData.sum.toFixed(2)}`, 
                this.incomeData.labels, 
                this.incomeData.data
            );
            
            createChart(
                'expenseChart', 
                `Expense: $${this.expenseData.sum.toFixed(2)}`, 
                this.expenseData.labels, 
                this.expenseData.data
            );
        }
    }));
});
