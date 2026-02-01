document.addEventListener('alpine:init', () => {
    Alpine.data('state', () => ({
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        transactions: [],
        incomeCategories: [],
        expenseCategories: [],
        accounts: [],
        incomeChart: null,
        expenseChart: null,
        isLoading: false,
        authStatus: 'checking',
        sessionId: null,
        qrCodeUrl: null,
        authInterval: null,

        init() {
            this.$watch('startDate', () => this.fetchTransactions());
            this.$watch('endDate', () => this.fetchTransactions());
            this.checkAuthAndFetch();
        },

        async checkAuthAndFetch() {
            this.authStatus = 'checking';
            try {
                await this.fetchTransactions();
                this.authStatus = 'authenticated';
            } catch (error) {
                if (error instanceof Error && (error.message.includes('401') || error.message.includes('403'))) {
                    await this.startAuthFlow();
                } else {
                    console.error('Error:', error);
                    this.authStatus = 'error';
                }
            }
        },

        async startAuthFlow() {
            this.authStatus = 'unauthenticated';
            const response = await fetch('http://localhost:8000/create-session', {method: 'POST'});
            if (!response.ok) {
                throw new Error(`${response.status} ${response.statusText}`);
            }
            const { session_id } = await response.json();
            console.log(response);
            this.sessionId = session_id;
            this.qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${session_id}`;
            
            this.authInterval = setInterval(async () => {
                try {
                    const authResponse = await fetch(`http://localhost:8000/auth/${this.sessionId}`, {credentials: 'include'});
                    const { status } = await authResponse.json();
                    
                    if (status === 'confirmed') {
                        clearInterval(this.authInterval);
                        await this.checkAuthAndFetch();
                    }
                } catch (error) {
                    console.error('Auth polling error:', error);
                }
            }, 2000);
        },

        async fetchTransactions() {
            this.isLoading = true;
            try {
                const response = await fetch(`http://localhost:8000/transactions?date_from=${this.startDate}&date_to=${this.endDate}`, {
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    throw new Error(response.status.toString());
                }
                
                const data = await response.json();
                this.transactions = data.transactions;
                
                this.incomeCategories = [...new Set(
                    this.transactions
                        .filter(t => t.type === 'income')
                        .map(t => t.category)
                )];
                
                this.expenseCategories = [...new Set(
                    this.transactions
                        .filter(t => t.type === 'expense')
                        .map(t => t.category)
                )];
                
                this.accounts = [...new Set(this.transactions.map(t => t.account))];
                
                this.updateCharts();
            } catch (error) {
                console.error('Error fetching transactions:', error);
                throw error;
            } finally {
                this.isLoading = false;
            }
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

            // Destroy existing chart if it exists
            if (this[chartId]) {
                this[chartId].destroy();
            }

            // Create new chart instance
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
                            text: `${titlePrefix}: $${chartData.sum.toFixed(2)}`,
                            font: {
                                size: 16
                            }
                        },
                        datalabels: {
                            formatter: (value, context) => {
                                const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = (value / total) * 100;
                                // Only show label if segment is > 5% of total
                                if (percentage < 5) return '';
                                return `${value.toFixed(2)}\n(${Math.round(percentage)}%)`;
                            },
                            color: '#fff',
                            font: {
                                weight: 'bold',
                                size: 12
                            },
                            textAlign: 'center',
                            padding: 6
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: $${value.toFixed(2)} (${percentage}%)`;
                                }
                            }
                        }
                    }
                },
                plugins: [ChartDataLabels]
            });
        }
    }));
});
