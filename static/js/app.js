// Modern web app for Roth conversion simulator

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Load states
    const response = await fetch('/api/states');
    const states = await response.json();
    
    const stateSelect = document.getElementById('stateResidence');
    states.forEach(state => {
        const option = document.createElement('option');
        option.value = state;
        option.textContent = state;
        stateSelect.appendChild(option);
    });
    
    // Load account types
    const accResponse = await fetch('/api/account-types');
    const accountTypes = await accResponse.json();
    
    const accTypeSelect = document.getElementById('accType');
    accountTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        accTypeSelect.appendChild(option);
    });
    
    // Set up event listeners
    setupEventListeners();
    
    // Load existing data
    await loadAccountsList();
    await loadIncomeList();
}

function setupEventListeners() {
    // Birth year calculation
    document.getElementById('birthYear').addEventListener('change', (e) => {
        const year = parseInt(e.target.value);
        const age = new Date().getFullYear() - year;
        document.getElementById('ageDisplay').textContent = age ? `(Age ${age})` : '';
    });
    
    // Spouse birth year calculation
    document.getElementById('spouseBirthYear').addEventListener('change', (e) => {
        const year = parseInt(e.target.value);
        const age = new Date().getFullYear() - year;
        document.getElementById('spouseAgeDisplay').textContent = age ? `(Age ${age})` : '';
    });
    
    // Annual to monthly expense calculation
    document.getElementById('annualExpense').addEventListener('change', (e) => {
        const annual = parseFloat(e.target.value) || 0;
        const monthly = (annual / 12).toFixed(0);
        document.getElementById('monthlyExpense').value = monthly;
    });
    
    // Marital status change
    document.getElementById('maritalStatus').addEventListener('change', updateSpouseFields);
}

function updateSpouseFields() {
    const maritalStatus = document.getElementById('maritalStatus').value;
    const spouseContainer = document.getElementById('spouseContainer');
    const spouseBirthYear = document.getElementById('spouseBirthYear');
    
    if (maritalStatus === 'married') {
        spouseContainer.style.display = 'flex';
        spouseBirthYear.required = true;
    } else {
        spouseContainer.style.display = 'none';
        spouseBirthYear.required = false;
        spouseBirthYear.value = '';
    }
}

// Tab switching
function switchTab(tabName) {
    // Hide all panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected panel
    document.getElementById(tabName).classList.add('active');
    
    // Add active to button
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

// Client Info
async function saveClient() {
    const firstName = document.getElementById('firstName').value;
    const lastName = document.getElementById('lastName').value;
    const birthYear = document.getElementById('birthYear').value;
    const spouseBirthYear = document.getElementById('spouseBirthYear').value;
    const state = document.getElementById('stateResidence').value;
    const filingStatus = document.getElementById('filingStatus').value;
    
    if (!firstName || !lastName || !birthYear || !state) {
        alert('Please fill in all required fields');
        return;
    }
    
    const response = await fetch('/api/save-client', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            first_name: firstName,
            last_name: lastName,
            birth_year: birthYear,
            spouse_birth_year: spouseBirthYear,
            state_residence: state,
            filing_status: filingStatus,
        })
    });
    
    const data = await response.json();
    if (data.success) {
        showNotification('✓ Client information saved!', 'success');
        generateClientSuggestions();
    } else {
        showNotification('Error: ' + data.error, 'error');
    }
}

function generateClientSuggestions() {
    const birthYear = parseInt(document.getElementById('birthYear').value);
    const spouseBirthYear = parseInt(document.getElementById('spouseBirthYear').value);
    const currentYear = new Date().getFullYear();
    
    const age = currentYear - birthYear;
    const spouseAge = spouseBirthYear ? currentYear - spouseBirthYear : null;
    
    const suggestions = [];
    
    if (age < 59.5) {
        suggestions.push('💡 Before 59½: Consider Roth conversions to establish tax-free growth and avoid early withdrawal penalties');
    } else if (age < 62) {
        suggestions.push('💡 Ages 59½-62: Active conversion window before Social Security and IRMAA thresholds');
    } else if (age < 73) {
        suggestions.push('💡 Ages 62-72: Optimal conversion years before Required Minimum Distributions begin');
    } else {
        suggestions.push('💡 Age 73+: RMDs are required; strategic conversions to manage tax brackets');
    }
    
    if (spouseAge && spouseAge > age) {
        suggestions.push(`💡 Spouse is ${spouseAge - age} years younger - extended planning horizon for conversions`);
    }
    
    const suggestionsDiv = document.getElementById('clientSuggestions');
    suggestionsDiv.innerHTML = suggestions.map(s => `<div class="suggestion-item">${s}</div>`).join('');
}

// Accounts
async function addAccount() {
    const name = document.getElementById('accName').value;
    const type = document.getElementById('accType').value;
    const balance = document.getElementById('accBalance').value;
    const pretax = document.getElementById('accPretax').value;
    const aftertax = document.getElementById('accAftertax').value;
    const growth = document.getElementById('accGrowth').value;
    const contrib = document.getElementById('accContrib').value;
    
    if (!name || !type || !balance || !pretax || !aftertax) {
        alert('Please fill in all required fields');
        return;
    }
    
    const response = await fetch('/api/save-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name,
            type,
            balance,
            pretax,
            aftertax,
            growth,
            contribution: contrib,
        })
    });
    
    const data = await response.json();
    if (data.success) {
        showNotification(`✓ ${name} added!`, 'success');
        clearAccountForm();
        await loadAccountsList();
    } else {
        showNotification('Error: ' + data.error, 'error');
    }
}

function clearAccountForm() {
    document.getElementById('accName').value = '';
    document.getElementById('accType').value = '';
    document.getElementById('accBalance').value = '';
    document.getElementById('accPretax').value = '';
    document.getElementById('accAftertax').value = '';
    document.getElementById('accGrowth').value = '7';
    document.getElementById('accContrib').value = '0';
}

async function loadAccountsList() {
    const response = await fetch('/api/get-accounts');
    const accounts = await response.json();
    
    const list = document.getElementById('accountsList');
    
    if (accounts.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary);">No accounts added yet</p>';
        return;
    }
    
    list.innerHTML = accounts.map((acc, idx) => `
        <div class="list-item">
            <div class="list-item-content">
                <div class="list-item-title">${acc.name}</div>
                <div class="list-item-meta">
                    ${acc.type} • Balance: $${parseFloat(acc.balance).toLocaleString('en-US', {maximumFractionDigits: 0})} 
                    • Growth: ${(acc.growth * 100).toFixed(1)}%
                </div>
            </div>
            <div class="list-item-actions">
                <button class="btn-danger" onclick="deleteAccount(${idx})">✕ Delete</button>
            </div>
        </div>
    `).join('');
}

async function deleteAccount(index) {
    if (confirm('Delete this account?')) {
        const response = await fetch(`/api/delete-account/${index}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            showNotification('Account deleted', 'success');
            await loadAccountsList();
        }
    }
}

// Income
async function addIncome() {
    const type = document.getElementById('incomeType').value;
    const amount = document.getElementById('incomeAmount').value;
    const startAge = document.getElementById('incomeStartAge').value;
    const endAge = document.getElementById('incomeEndAge').value;
    const growth = document.getElementById('incomeGrowth').value;
    
    if (!type || !amount) {
        alert('Please fill in all required fields');
        return;
    }
    
    const response = await fetch('/api/save-income', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type,
            amount,
            start_age: startAge,
            end_age: endAge,
            growth,
        })
    });
    
    const data = await response.json();
    if (data.success) {
        showNotification(`✓ ${type} income added!`, 'success');
        clearIncomeForm();
        await loadIncomeList();
    } else {
        showNotification('Error: ' + data.error, 'error');
    }
}

function clearIncomeForm() {
    document.getElementById('incomeType').value = '';
    document.getElementById('incomeAmount').value = '';
    document.getElementById('incomeStartAge').value = '67';
    document.getElementById('incomeEndAge').value = '100';
    document.getElementById('incomeGrowth').value = '0';
}

async function loadIncomeList() {
    const response = await fetch('/api/get-income');
    const income = await response.json();
    
    const list = document.getElementById('incomeList');
    
    if (income.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary);">No income streams added yet</p>';
        return;
    }
    
    list.innerHTML = income.map((inc, idx) => `
        <div class="list-item">
            <div class="list-item-content">
                <div class="list-item-title">${inc.type}</div>
                <div class="list-item-meta">
                    Annual: $${parseFloat(inc.amount).toLocaleString('en-US', {maximumFractionDigits: 0})} 
                    • Ages ${inc.start_age}-${inc.end_age} 
                    • Growth: ${(inc.growth * 100).toFixed(1)}%
                </div>
            </div>
            <div class="list-item-actions">
                <button class="btn-danger" onclick="deleteIncome(${idx})">✕ Delete</button>
            </div>
        </div>
    `).join('');
}

async function deleteIncome(index) {
    if (confirm('Delete this income stream?')) {
        const response = await fetch(`/api/delete-income/${index}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            showNotification('Income stream deleted', 'success');
            await loadIncomeList();
        }
    }
}

// Expenses
async function saveExpenses() {
    const annual = document.getElementById('annualExpense').value;
    const inflation = document.getElementById('inflationRate').value;
    const healthcare = document.getElementById('healthcareCost').value;
    const ltc = document.getElementById('ltcReserve').value;
    
    if (!annual) {
        alert('Please enter annual expenses');
        return;
    }
    
    const response = await fetch('/api/save-expenses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            annual,
            inflation,
            healthcare,
            ltc,
        })
    });
    
    const data = await response.json();
    if (data.success) {
        showNotification('✓ Expenses saved!', 'success');
        generateExpenseSuggestions();
    } else {
        showNotification('Error: ' + data.error, 'error');
    }
}

function generateExpenseSuggestions() {
    const annual = parseFloat(document.getElementById('annualExpense').value) || 0;
    const suggestions = [];
    
    const monthly = (annual / 12).toFixed(0);
    suggestions.push(`💡 Monthly spending: $${parseInt(monthly).toLocaleString()} (${(annual / 12 / 1000).toFixed(1)}k/month)`);
    
    if (annual < 50000) {
        suggestions.push('💡 Modest expenses ($50k/year) - favorable for Roth conversions to control tax brackets');
    } else if (annual < 100000) {
        suggestions.push('💡 Mid-range expenses - balance conversions with lifestyle needs');
    } else {
        suggestions.push('💡 Higher expenses - strategic conversions to minimize tax drag on cash flow');
    }
    
    suggestions.push('💡 Rule of thumb: 70% of pre-retirement income is typical retirement spending');
    
    const suggestionsDiv = document.getElementById('expenseSuggestions');
    suggestionsDiv.innerHTML = suggestions.map(s => `<div class="suggestion-item">${s}</div>`).join('');
}

// Analysis
async function runAnalysis() {
    // Validate completion
    const birthYear = document.getElementById('birthYear').value;
    const stateResidence = document.getElementById('stateResidence').value;
    const annualExpense = document.getElementById('annualExpense').value;
    
    if (!birthYear || !stateResidence || !annualExpense) {
        alert('Please complete Client Info and Expenses sections');
        return;
    }
    
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '⏳ Running Analysis...';
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                projection_years: document.getElementById('projectionYears').value,
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.results);
            switchTab('results');
            showNotification('✓ Analysis complete!', 'success');
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 Run Analysis';
    }
}

function displayResults(results) {
    const content = document.getElementById('resultsContent');
    
    // Summary cards
    const summaryHTML = `
        <div class="results-grid">
            <div class="result-card">
                <div class="result-card-title">Total Assets</div>
                <div class="result-card-value">$${(results.total_balance / 1000000).toFixed(1)}M</div>
            </div>
            <div class="result-card">
                <div class="result-card-title">Annual Income</div>
                <div class="result-card-value">$${(results.total_income / 1000).toFixed(0)}k</div>
            </div>
            <div class="result-card">
                <div class="result-card-title">Annual Expenses</div>
                <div class="result-card-value">$${(results.annual_expenses / 1000).toFixed(0)}k</div>
            </div>
            <div class="result-card">
                <div class="result-card-title">Accounts</div>
                <div class="result-card-value">${results.total_accounts}</div>
            </div>
        </div>
    `;
    
    // Strategies table
    const strategiesHTML = `
        <h3 style="margin-top: 2rem; margin-bottom: 1rem; color: var(--text-primary);">Optimization Strategies</h3>
        <table class="strategies-table">
            <thead>
                <tr>
                    <th>Strategy</th>
                    <th>Conversions</th>
                    <th>Total Taxes</th>
                    <th>Final Roth</th>
                    <th>Final Net Worth</th>
                </tr>
            </thead>
            <tbody>
                ${results.strategies.map(s => `
                    <tr>
                        <td><strong>${s.name}</strong><br><small>${s.objective}</small></td>
                        <td>$${(s.total_conversions / 1000).toFixed(0)}k</td>
                        <td>$${(s.total_taxes / 1000).toFixed(0)}k</td>
                        <td>$${(s.final_roth / 1000000).toFixed(2)}M</td>
                        <td><strong>$${(s.final_networth / 1000000).toFixed(2)}M</strong></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    content.innerHTML = summaryHTML + strategiesHTML;
}

// Help
function showHelp() {
    const helpText = `
ROTH CONVERSION SIMULATOR - HELP

This tool helps you optimize your Roth conversion strategy by:
1. Modeling your current financial situation
2. Projecting income, expenses, and account growth
3. Calculating taxes, RMDs, and IRMAA impacts
4. Comparing multiple conversion strategies
5. Providing personalized recommendations

GETTING STARTED:
1. Fill in your personal information (Client Info tab)
2. Enter all retirement accounts (Accounts tab)
3. Add income sources (Income tab)
4. Set spending projections (Expenses tab)
5. Click "Run Analysis" to see results

KEY CONCEPTS:
• Roth Conversion: Moving money from pre-tax to tax-free accounts
• Pro-rata Rule: How taxable conversions are calculated
• IRMAA: Income-Related Monthly Adjustment Amount (Medicare premiums)
• RMD: Required Minimum Distributions (mandatory at age 73+)

INTERPRETATION:
• Final Net Worth: Total projected wealth at age 100
• Final Roth Value: Tax-free Roth account balance
• Total Taxes Paid: Cumulative tax liability
• IRMAA Costs: Additional Medicare premiums

Questions? Review field definitions or consult IRS publications.
    `;
    
    alert(helpText);
}

// Session
async function clearSession() {
    if (confirm('Clear all data and start over?')) {
        await fetch('/api/clear-session', { method: 'POST' });
        location.reload();
    }
}

// Notifications
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// International Tax Strategies
async function loadIntlStrategies() {
    try {
        const response = await fetch('/api/international-strategies');
        const strategies = await response.json();
        
        let html = '<div style="margin-top: 2rem;">';
        
        strategies.forEach(strategy => {
            html += `
                <div class="intl-strategy-card">
                    <div class="intl-strategy-title">${strategy.name}</div>
                    <div class="intl-strategy-description">${strategy.description}</div>
                    
                    <div class="intl-strategy-meta">
                        <div class="meta-item">
                            <span class="meta-label">Tax Savings</span>
                            <span class="meta-value">${strategy.tax_savings}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Complexity</span>
                            <span class="meta-value">${strategy.complexity}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Risk Level</span>
                            <span class="meta-value">${strategy.risk}</span>
                        </div>
                    </div>
                    
                    <div class="requirements-list">
                        <h5>Key Requirements:</h5>
                        <ul>
                            ${strategy.requirements.map(req => `<li>${req}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div style="margin-top: var(--spacing-md); padding-top: var(--spacing-md); border-top: 1px solid var(--border-color);">
                        <small style="color: var(--text-secondary);">
                            Available in: ${strategy.countries.join(', ')}
                        </small>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        document.getElementById('intlStrategiesContent').innerHTML = html;
        showNotification('✓ Loaded ' + strategies.length + ' international strategies', 'success');
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

async function compareIntlStrategies() {
    const income = document.getElementById('intlIncome').value;
    const rate = document.getElementById('intlCurrentRate').value;
    const years = document.getElementById('intlYears').value;
    
    if (!income) {
        alert('Please enter annual income');
        return;
    }
    
    try {
        const response = await fetch('/api/strategy-comparison', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                income: parseFloat(income),
                rate: parseFloat(rate) / 100,
                years: parseInt(years),
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            let html = '<h3 style="margin-top: 2rem; margin-bottom: 1rem; color: var(--text-primary);">Tax Strategy Comparison</h3>';
            html += '<table class="comparison-table"><thead><tr><th>Strategy</th><th>Annual Tax</th><th>Effective Rate</th><th>Lifetime Tax</th><th class="highlight">Lifetime Savings</th></tr></thead><tbody>';
            
            data.strategies.forEach(s => {
                html += `
                    <tr>
                        <td><strong>${s.name}</strong></td>
                        <td>$${(s.annual_tax / 1000).toFixed(1)}k</td>
                        <td>${(s.rate * 100).toFixed(1)}%</td>
                        <td>$${(s.lifetime_tax / 1000000).toFixed(2)}M</td>
                        <td class="highlight">$${(s.lifetime_savings / 1000000).toFixed(2)}M</td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            document.getElementById('intlStrategiesContent').innerHTML = html;
            showNotification('✓ Comparison complete!', 'success');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

// Advanced Strategies
async function calculateBackdoorRoth() {
    const amount = parseFloat(document.getElementById('backdroorAmount').value) || 0;
    const taxRate = parseFloat(document.getElementById('backdroorTaxRate').value) / 100 || 0;
    const years = parseInt(document.getElementById('backdroorYears').value) || 30;
    const growth = parseFloat(document.getElementById('backdroorGrowth').value) / 100 || 0.07;
    
    try {
        const response = await fetch('/api/backdoor-roth-calculation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount,
                tax_rate: taxRate,
                years,
                growth,
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const html = `
                <div class="info-box">
                    <h4>Backdoor Roth Analysis</h4>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <span class="metric-label">Conversion Amount</span>
                            <span class="metric-value">$${(data.conversion_amount / 1000).toFixed(1)}k</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-label">Immediate Tax</span>
                            <span class="metric-value">$${(data.tax_owed / 1000).toFixed(1)}k</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-label">Future Value</span>
                            <span class="metric-value">$${(data.future_value / 1000).toFixed(1)}k</span>
                        </div>
                        <div class="metric-card" style="background: rgba(16, 185, 129, 0.1); border-color: var(--success-color);">
                            <span class="metric-label">Net Benefit</span>
                            <span class="metric-value" style="color: var(--success-color);">$${(data.net_benefit / 1000).toFixed(1)}k</span>
                        </div>
                    </div>
                    <p style="margin-top: 1rem; color: var(--text-secondary);">
                        By converting $${(data.conversion_amount / 1000).toFixed(1)}k to Roth, you'll save <strong>$${(data.net_benefit / 1000).toFixed(1)}k</strong> 
                        in taxes over ${years} years (${data.benefit_percentage}% benefit).
                    </p>
                </div>
            `;
            document.getElementById('backdroorResults').innerHTML = html;
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

async function calculateMegaBackdoor() {
    const income = parseFloat(document.getElementById('megaIncome').value) || 0;
    
    // Solo 401(k) limit 2024: $69,000 ($76,500 with catch-up)
    // Employee deferral: $23,500 ($31,000 with catch-up)
    // Employer profit sharing: 20% of net self-employment income
    
    const maxMega = 69000;
    document.getElementById('megaMax').value = maxMega.toLocaleString();
    
    const html = `
        <div class="info-box">
            <h4>Mega Backdoor Roth Capacity</h4>
            <div class="metrics-grid">
                <div class="metric-card">
                    <span class="metric-label">Maximum Contribution</span>
                    <span class="metric-value">$${maxMega.toLocaleString()}</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">Employee Deferral</span>
                    <span class="metric-value">$23,500</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">Employer Match (20%)</span>
                    <span class="metric-value">$${(income * 0.20 / 1000).toFixed(0)}k</span>
                </div>
            </div>
            <p style="margin-top: 1rem; color: var(--text-secondary);">
                <strong>Note:</strong> Requires Solo 401(k) plan. Must make after-tax contributions and immediately convert to Roth (pro-rata rule applies).
            </p>
        </div>
    `;
    document.getElementById('megaResults').innerHTML = html;
}

function calculateSolo401k() {
    const income = parseFloat(document.getElementById('solo401kIncome').value) || 0;
    
    // 2024 limits
    const employeeDeferral = 23500;
    const employerContribution = income * 0.20;  // Approximately 20% for self-employed
    const totalContribution = employeeDeferral + employerContribution;
    
    const html = `
        <div class="info-box">
            <h4>Solo 401(k) Maximum Contribution</h4>
            <div class="metrics-grid">
                <div class="metric-card">
                    <span class="metric-label">Employee Deferral</span>
                    <span class="metric-value">$${employeeDeferral.toLocaleString()}</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">Employer Profit Sharing (20%)</span>
                    <span class="metric-value">$${(employerContribution / 1000).toFixed(0)}k</span>
                </div>
                <div class="metric-card" style="background: rgba(16, 185, 129, 0.1); border-color: var(--success-color);">
                    <span class="metric-label">Total Contribution</span>
                    <span class="metric-value" style="color: var(--success-color);">$${(totalContribution / 1000).toFixed(0)}k</span>
                </div>
            </div>
            <p style="margin-top: 1rem; color: var(--text-secondary);">
                With $${(income / 1000).toFixed(0)}k in net self-employment income, you can contribute up to <strong>$${(totalContribution / 1000).toFixed(0)}k</strong> 
                annually to your Solo 401(k). Can be split between Roth and Traditional.
            </p>
        </div>
    `;
    document.getElementById('solo401kResults').innerHTML = html;
}
