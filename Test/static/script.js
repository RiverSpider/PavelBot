class TinkoffMiniApp {
    constructor() {
        this.userId = null;
        this.telegram = null;
        this.initData = null;
        
        this.init();
    }

    async init() {
        try {
            // Инициализация Telegram Web App
            this.telegram = window.Telegram.WebApp;
            this.telegram.expand();
            
            // Получаем данные пользователя
            this.initData = this.telegram.initData;
            this.userId = this.telegram.initDataUnsafe.user.id;
            
            this.updateUserInfo();
            await this.checkUserSetup();
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Ошибка инициализации приложения');
        }
    }

    updateUserInfo() {
        const user = this.telegram.initDataUnsafe.user;
        const userInfo = document.getElementById('userInfo');
        
        if (user) {
            userInfo.innerHTML = `
                👤 ${user.first_name}${user.last_name ? ' ' + user.last_name : ''}
                ${user.username ? `(@${user.username})` : ''}
            `;
        }
    }

    async checkUserSetup() {
        try {
            showLoading(true);
            
            // Проверяем, установлен ли токен
            const token = await this.getStoredToken();
            
            if (!token) {
                this.showSetupSection();
                return;
            }
            
            // Проверяем валидность токена
            const isValid = await this.validateToken(token);
            
            if (!isValid) {
                this.showSetupSection();
                this.showStatus('Токен невалиден. Пожалуйста, обновите его.', 'error');
                return;
            }
            
            // Проверяем, выбраны ли счета
            const accounts = await this.getUserAccounts();
            
            if (!accounts || accounts.length === 0) {
                this.showAccountsSection();
                return;
            }
            
            // Все настроено, показываем дашборд
            this.showDashboard();
            
        } catch (error) {
            console.error('Setup check error:', error);
            this.showError('Ошибка проверки настроек');
        } finally {
            showLoading(false);
        }
    }

    async getStoredToken() {
        // В реальном приложении токен должен храниться на сервере
        // Здесь имитируем получение токена
        return localStorage.getItem(`tinkoff_token_${this.userId}`);
    }

    async validateToken(token) {
        try {
            const response = await fetch('/api/set_token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    token: token
                })
            });
            
            const data = await response.json();
            return data.valid;
            
        } catch (error) {
            console.error('Token validation error:', error);
            return false;
        }
    }

    async getUserAccounts() {
        try {
            const response = await fetch(`/api/accounts?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.error) {
                return [];
            }
            
            // Проверяем, есть ли сохраненные счета
            const savedAccounts = JSON.parse(localStorage.getItem(`user_accounts_${this.userId}`) || '[]');
            return savedAccounts;
            
        } catch (error) {
            console.error('Get accounts error:', error);
            return [];
        }
    }

    showSetupSection() {
        hideAllSections();
        document.getElementById('setupSection').classList.remove('hidden');
    }

    showAccountsSection() {
        hideAllSections();
        document.getElementById('accountsSection').classList.remove('hidden');
        this.loadAccountsList();
    }

    showDashboard() {
        hideAllSections();
        document.getElementById('dashboardSection').classList.remove('hidden');
        this.loadDashboardData();
    }

    async loadAccountsList() {
        try {
            const response = await fetch(`/api/accounts?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.error) {
                this.showStatus('Ошибка загрузки счетов', 'error');
                return;
            }
            
            const accountsList = document.getElementById('accountsList');
            const savedAccounts = JSON.parse(localStorage.getItem(`user_accounts_${this.userId}`) || '[]');
            
            accountsList.innerHTML = `
                <div class="accounts-list">
                    ${data.accounts.map(account => `
                        <div class="account-item">
                            <div class="account-info">
                                <h4>${account.name}</h4>
                                <div class="account-meta">
                                    ${account.type} • ${account.portfolio_value.toLocaleString('ru-RU')} ₽
                                </div>
                            </div>
                            <input type="checkbox" 
                                   class="account-select" 
                                   value="${account.id}"
                                   ${savedAccounts.includes(account.id) ? 'checked' : ''}>
                        </div>
                    `).join('')}
                </div>
            `;
            
        } catch (error) {
            console.error('Load accounts error:', error);
            this.showStatus('Ошибка загрузки счетов', 'error');
        }
    }

    async loadDashboardData() {
        await this.loadPortfolio();
        await this.loadCharts();
    }

    async loadPortfolio() {
        try {
            showLoading(true);
            
            const response = await fetch(`/api/portfolio?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.error) {
                this.showStatus('Ошибка загрузки портфеля', 'error');
                return;
            }
            
            this.updatePortfolioSummary(data);
            this.updatePositionsList(data.positions);
            
        } catch (error) {
            console.error('Load portfolio error:', error);
            this.showStatus('Ошибка загрузки портфеля', 'error');
        } finally {
            showLoading(false);
        }
    }

    updatePortfolioSummary(data) {
        const summaryElement = document.getElementById('portfolioSummary');
        
        summaryElement.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 2rem; font-weight: bold; color: #00A2FF; margin-bottom: 10px;">
                    ${data.total_value.toLocaleString('ru-RU')} ₽
                </div>
                <div style="color: #B0B0B0;">
                    Общая стоимость портфеля
                </div>
                <div style="margin-top: 15px; display: flex; justify-content: center; gap: 20px;">
                    <div>
                        <div style="font-size: 0.9rem; color: #B0B0B0;">Акции</div>
                        <div style="font-weight: bold;">${data.stocks.length}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.9rem; color: #B0B0B0;">Облигации</div>
                        <div style="font-weight: bold;">${data.bonds.length}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.9rem; color: #B0B0B0;">Фонды</div>
                        <div style="font-weight: bold;">${data.etfs.length}</div>
                    </div>
                </div>
            </div>
        `;
    }

    updatePositionsList(positions) {
        const positionsList = document.getElementById('positionsList');
        
        if (!positions || positions.length === 0) {
            positionsList.innerHTML = '<p style="text-align: center; color: #B0B0B0;">Нет позиций</p>';
            return;
        }
        
        // Сортируем по стоимости
        const sortedPositions = positions.sort((a, b) => b.value - a.value);
        
        positionsList.innerHTML = `
            ${sortedPositions.slice(0, 10).map(position => `
                <div class="position-item">
                    <div class="position-name">${position.name}</div>
                    <div class="position-details">
                        <div class="position-value">${position.value.toLocaleString('ru-RU')} ₽</div>
                        <div class="position-yield ${position.yield >= 0 ? 'positive' : 'negative'}">
                            ${position.yield >= 0 ? '+' : ''}${position.yield.toLocaleString('ru-RU')} ₽
                        </div>
                    </div>
                </div>
            `).join('')}
            
            ${positions.length > 10 ? `
                <div style="text-align: center; margin-top: 15px; color: #B0B0B0;">
                    + еще ${positions.length - 10} позиций
                </div>
            ` : ''}
        `;
    }

    async loadCharts() {
        await this.loadCapitalChart();
        await this.loadIncomeChart();
    }

    async loadCapitalChart() {
        try {
            const response = await fetch(`/api/chart/capital?user_id=${this.userId}&period=week`);
            const data = await response.json();
            
            if (data.chart) {
                document.getElementById('capitalChart').innerHTML = `
                    <img src="data:image/png;base64,${data.chart}" alt="График капитала" class="chart-image">
                `;
            }
            
        } catch (error) {
            console.error('Load capital chart error:', error);
        }
    }

    async loadIncomeChart() {
        try {
            const response = await fetch(`/api/chart/income?user_id=${this.userId}&period=week`);
            const data = await response.json();
            
            if (data.chart) {
                document.getElementById('incomeChart').innerHTML = `
                    <img src="data:image/png;base64,${data.chart}" alt="График доходности" class="chart-image">
                `;
            }
            
        } catch (error) {
            console.error('Load income chart error:', error);
        }
    }

    async showIncome(period) {
        try {
            showLoading(true);
            
            const response = await fetch(`/api/income?user_id=${this.userId}&period=${period}`);
            const data = await response.json();
            
            if (data.error) {
                this.showStatus('Ошибка загрузки доходности', 'error');
                return;
            }
            
            this.showIncomeModal(data, period);
            
        } catch (error) {
            console.error('Show income error:', error);
            this.showStatus('Ошибка загрузки доходности', 'error');
        } finally {
            showLoading(false);
        }
    }

    showIncomeModal(data, period) {
        const periodNames = {
            'day': 'день',
            'week': 'неделю',
            'month': 'месяц',
            'year': 'год',
            'all_time': 'все время'
        };
        
        const periodName = periodNames[period] || period;
        
        // Здесь можно реализовать модальное окно с детальной информацией о доходности
        alert(`
            📊 Доходность за ${periodName}:
            
            💰 Общий доход: ${data.total_income.toLocaleString('ru-RU')} ₽
            🎯 От облигаций: ${data.bond_income.toLocaleString('ru-RU')} ₽
            💵 От дивидендов: ${data.dividend_income.toLocaleString('ru-RU')} ₽
            💸 Комиссии: ${data.commission_expenses.toLocaleString('ru-RU')} ₽
            💎 Чистый доход: ${(data.total_income - data.commission_expenses).toLocaleString('ru-RU')} ₽
        `);
    }

    showStatus(message, type = 'info') {
        // Удаляем предыдущие статусы
        document.querySelectorAll('.status').forEach(el => el.remove());
        
        const statusElement = document.createElement('div');
        statusElement.className = `status ${type}`;
        statusElement.textContent = message;
        
        // Добавляем статус в первую секцию
        const firstSection = document.querySelector('.section:not(.hidden)');
        firstSection.insertBefore(statusElement, firstSection.firstChild);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            statusElement.remove();
        }, 5000);
    }

    showError(message) {
        this.showStatus(message, 'error');
    }
}

// Глобальные функции для вызова из HTML
async function setToken() {
    const tokenInput = document.getElementById('apiToken');
    const token = tokenInput.value.trim();
    
    if (!token) {
        app.showStatus('Введите API токен', 'error');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/set_token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: app.userId,
                token: token
            })
        });
        
        const data = await response.json();
        
        if (data.valid) {
            // Сохраняем токен локально (в реальном приложении это должно быть на сервере)
            localStorage.setItem(`tinkoff_token_${app.userId}`, token);
            app.showStatus('Токен успешно сохранен и проверен!', 'success');
            
            // Переходим к выбору счетов
            setTimeout(() => app.showAccountsSection(), 1000);
            
        } else {
            app.showStatus('Неверный токен. Проверьте правильность ввода.', 'error');
        }
        
    } catch (error) {
        console.error('Set token error:', error);
        app.showStatus('Ошибка сохранения токена', 'error');
    } finally {
        showLoading(false);
    }
}

async function saveAccounts() {
    const selectedAccounts = Array.from(document.querySelectorAll('.account-select:checked'))
        .map(checkbox => checkbox.value);
    
    if (selectedAccounts.length === 0) {
        app.showStatus('Выберите хотя бы один счет', 'error');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/set_accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: app.userId,
                account_ids: selectedAccounts
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Сохраняем выбор локально
            localStorage.setItem(`user_accounts_${app.userId}`, JSON.stringify(selectedAccounts));
            app.showStatus('Счета успешно сохранены!', 'success');
            
            // Переходим к дашборду
            setTimeout(() => app.showDashboard(), 1000);
            
        } else {
            app.showStatus('Ошибка сохранения счетов', 'error');
        }
        
    } catch (error) {
        console.error('Save accounts error:', error);
        app.showStatus('Ошибка сохранения счетов', 'error');
    } finally {
        showLoading(false);
    }
}

// Вспомогательные функции
function hideAllSections() {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.style.display = 'block';
    } else {
        loading.style.display = 'none';
    }
}

// Глобальные функции для кнопок
function loadPortfolio() {
    app.loadPortfolio();
}

function showIncome(period) {
    app.showIncome(period);
}

// Инициализация приложения
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new TinkoffMiniApp();
});
