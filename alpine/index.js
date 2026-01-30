document.addEventListener('alpine:init', () => {
    Alpine.data('state', () => ({
        startDate: '',
        endDate: '',
        init() {
            this.startDate = new Date().toISOString().split('T')[0];
            this.endDate = new Date().toISOString().split('T')[0];
            console.log(this.startDate);
        }

    }));
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
                category: 'family',
                type: 'expense',
                amount: 50000.00
            }
        ],
        incomeCategories: ['salary', 'present'],
        expenseCategories: ['food', 'family', 'transport'],
        accounts: ['main'],
    });
});
