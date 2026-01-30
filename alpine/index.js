document.addEventListener('alpine:init', () => {
    Alpine.data('state', () => ({
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        transactions: [
            {
                id: 1,
                account: 'main',
                category: 'salary',
                type: 'income',
                amount: 100000.00
            },
            {
                id: 2,
                account: 'main',
                category: 'present',
                type: 'income',
                amount: 100000.00
            },
            {
                id: 3,
                account: 'main',
                category: 'family',
                type: 'expense',
                amount: 50000.00
            },
            {
                id: 4,
                account: 'main',
                category: 'food',
                type: 'expense',
                amount: 50000.00
            },
            {
                id: 5,
                account: 'main',
                category: 'transport',
                type: 'expense',
                amount: 1000.00
            }
        ],
        incomeCategories: ['salary', 'present'],
        expenseCategories: ['food', 'family', 'transport'],
        accounts: ['main'],
        incomeChart: null,
        expenseChart: null,

        init() {
            this.$watch('transactions', () => this.updateCharts());
            this.updateCharts();
        },

        addTransaction() {
            // Create a more varied sample transaction
            const types = ['income', 'expense'];
            const type = types[Math.floor(Math.random() * types.length)];
            const categories = type === 'income' ? this.incomeCategories : this.expenseCategories;
            const category = categories[Math.floor(Math.random() * categories.length)];
            const amount = type === 'income' 
                ? Math.floor(Math.random() * 5000) + 1000 
                : -(Math.floor(Math.random() * 500) + 50);
            
            this.transactions.push({
                id: Date.now(), // Use timestamp for unique ID
                account: 'main',
                category: category,
                type: type,
                amount: amount
            });
            this.updateCharts();
        },

        get incomeData() {
            const income = this.transactions.filter(t => t.type === 'income');
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
            const expense = this.transactions.filter(t => t.type === 'expense');
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
            this.updateChart('incomeChart', this.incomeData, 'Income');
            this.updateChart('expenseChart', this.expenseData, 'Expense');
        },

        updateChart(chartId, chartData, titlePrefix) {
            const ctx = document.getElementById(chartId);
            if (!ctx) return;

            const chart = this[chartId];
            const title = `${titlePrefix}: $${chartData.sum.toFixed(2)}`;

            if (chart) {
                chart.data.labels = chartData.labels;
                chart.data.datasets[0].data = chartData.data;
                chart.options.plugins.title.text = title;
                chart.update();
            } else {
                this[chartId] = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            data: chartData.data,
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
    }));
});
