// Modern web app for Roth conversion simulator

// ============= Tab Switching =============
function switchTab(tabName) {
    // Hide all panels
    const panels = document.querySelectorAll('.tab-panel');
    panels.forEach(panel => panel.classList.remove('active'));
    
    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected panel
    const selectedPanel = document.getElementById(tabName);
    if (selectedPanel) {
        selectedPanel.classList.add('active');
    }
    
    // Mark button as active
    const activeButton = document.querySelector(`button[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
}

// ============= Client Info =============
function updateSpouseField() {
    const maritalStatus = document.getElementById('maritalStatus').value;
    const spouseYearGroup = document.getElementById('spouseYearGroup');
    if (maritalStatus === 'Married') {
        spouseYearGroup.style.display = 'block';
    } else {
        spouseYearGroup.style.display = 'none';
    }
}

function saveClient() {
    const clientData = {
        firstName: document.getElementById('firstName').value,
        lastName: document.getElementById('lastName').value,
        birthYear: parseInt(document.getElementById('birthYear').value),
        maritalStatus: document.getElementById('maritalStatus').value,
        spouseBirthYear: document.getElementById('spouseBirthYear').value ? 
            parseInt(document.getElementById('spouseBirthYear').value) : null,
        state: document.getElementById('state').value,
        filingStatus: document.getElementById('filingStatus').value
    };
    
    // Validate required fields
    if (!clientData.firstName || !clientData.lastName || !clientData.birthYear || !clientData.state) {
        alert('Please fill in all required fields');
        return;
    }
    
    // Save to localStorage
    localStorage.setItem('clientData', JSON.stringify(clientData));
    alert('Client information saved!');
}

// ============= Accounts =============
let accounts = [];

function addAccount() {
    const account = {
        id: Date.now(),
        name: document.getElementById('accountName').value,
        type: document.getElementById('accountType').value,
        balance: parseFloat(document.getElementById('accountBalance').value) || 0,
        growth: parseFloat(document.getElementById('accountGrowth').value) || 7
    };
    
    if (!account.name || !account.type || account.balance <= 0) {
        alert('Please fill in all account fields');
        return;
    }
    
    accounts.push(account);
    localStorage.setItem('accounts', JSON.stringify(accounts));
    displayAccounts();
    
    // Clear form
    document.getElementById('accountName').value = '';
    document.getElementById('accountType').value = '';
    document.getElementById('accountBalance').value = '';
    document.getElementById('accountGrowth').value = '7';
}

function removeAccount(id) {
    accounts = accounts.filter(acc => acc.id !== id);
    localStorage.setItem('accounts', JSON.stringify(accounts));
    displayAccounts();
}

function displayAccounts() {
    const accountsList = document.getElementById('accountsList');
    accountsList.innerHTML = '';
    
    if (accounts.length === 0) {
        accountsList.innerHTML = '<p style="color: #888;">No accounts added yet. Add your first account above.</p>';
        return;
    }
    
    accounts.forEach(account => {
        const card = document.createElement('div');
        card.className = 'account-card';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4>${account.name}</h4>
                    <p><strong>${account.type}</strong> | Balance: $${account.balance.toLocaleString()} | Growth: ${account.growth}%</p>
                </div>
                <button class="btn-danger" onclick="removeAccount(${account.id})">Remove</button>
            </div>
        `;
        accountsList.appendChild(card);
    });
    
    // Display total balance
    const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0);
    const totalDiv = document.createElement('div');
    totalDiv.className = 'info-box';
    totalDiv.style.marginTop = '2rem';
    totalDiv.innerHTML = `<strong>Total Account Balance: $${totalBalance.toLocaleString()}</strong>`;
    accountsList.appendChild(totalDiv);
}

// ============= Income Streams =============
let incomeStreams = [];

function addIncome() {
    const income = {
        id: Date.now(),
        source: document.getElementById('incomeSource').value,
        amount: parseFloat(document.getElementById('incomeAmount').value) || 0,
        type: document.getElementById('incomeType').value,
        startYear: parseInt(document.getElementById('incomeStartYear').value)
    };
    
    if (!income.source || income.amount <= 0) {
        alert('Please fill in all income fields');
        return;
    }
    
    incomeStreams.push(income);
    localStorage.setItem('incomeStreams', JSON.stringify(incomeStreams));
    displayIncome();
    
    // Clear form
    document.getElementById('incomeSource').value = '';
    document.getElementById('incomeAmount').value = '';
    document.getElementById('incomeType').value = 'Ordinary';
    document.getElementById('incomeStartYear').value = new Date().getFullYear();
}

function removeIncome(id) {
    incomeStreams = incomeStreams.filter(inc => inc.id !== id);
    localStorage.setItem('incomeStreams', JSON.stringify(incomeStreams));
    displayIncome();
}

function displayIncome() {
    const incomeList = document.getElementById('incomeList');
    incomeList.innerHTML = '';
    
    if (incomeStreams.length === 0) {
        incomeList.innerHTML = '<p style="color: #888;">No income streams added yet. Add your first income stream above.</p>';
        return;
    }
    
    incomeStreams.forEach(income => {
        const card = document.createElement('div');
        card.className = 'account-card';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4>${income.source}</h4>
                    <p><strong>$${income.amount.toLocaleString()}/year</strong> | Type: ${income.type} | Starting: ${income.startYear}</p>
                </div>
                <button class="btn-danger" onclick="removeIncome(${income.id})">Remove</button>
            </div>
        `;
        incomeList.appendChild(card);
    });
    
    // Display total income
    const totalIncome = incomeStreams.reduce((sum, inc) => sum + inc.amount, 0);
    const totalDiv = document.createElement('div');
    totalDiv.className = 'info-box';
    totalDiv.style.marginTop = '2rem';
    totalDiv.innerHTML = `<strong>Total Annual Income: $${totalIncome.toLocaleString()}</strong>`;
    incomeList.appendChild(totalDiv);
}

// ============= Expenses =============
function saveExpenses() {
    const expenses = {
        basic: parseFloat(document.getElementById('basicExpenses').value) || 50000,
        health: parseFloat(document.getElementById('healthExpenses').value) || 10000,
        travel: parseFloat(document.getElementById('travelExpenses').value) || 15000,
        inflation: parseFloat(document.getElementById('inflationRate').value) || 2.5
    };
    
    localStorage.setItem('expenses', JSON.stringify(expenses));
    const total = expenses.basic + expenses.health + expenses.travel;
    alert(`Expenses saved! Total annual expenses: $${total.toLocaleString()}`);
}

// ============= Settings =============
function saveSettings() {
    const settings = {
        startYear: parseInt(document.getElementById('startYear').value),
        endYear: parseInt(document.getElementById('endYear').value),
        federalRate: parseFloat(document.getElementById('federalRate').value),
        stateRate: parseFloat(document.getElementById('stateRate').value),
        defaultGrowth: parseFloat(document.getElementById('defaultGrowth').value),
        withdrawalSequence: document.getElementById('withdrawalSequence').value,
        optimizationGoal: document.getElementById('optimizationGoal').value
    };
    
    localStorage.setItem('settings', JSON.stringify(settings));
    alert('Settings saved!');
}

// ============= Analysis & Results =============
async function runAnalysis() {
    const clientData = JSON.parse(localStorage.getItem('clientData') || '{}');
    const accounts = JSON.parse(localStorage.getItem('accounts') || '[]');
    const incomeStreams = JSON.parse(localStorage.getItem('incomeStreams') || '[]');
    const expenses = JSON.parse(localStorage.getItem('expenses') || '{}');
    const settings = JSON.parse(localStorage.getItem('settings') || '{}');
    
    if (!clientData.firstName || accounts.length === 0 || incomeStreams.length === 0) {
        alert('Please complete Client Info, Accounts, and Income sections first');
        return;
    }
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                client: clientData,
                accounts: accounts,
                income_streams: incomeStreams,
                expenses: expenses,
                settings: settings
            })
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const results = await response.json();
        displayResults(results);
        switchTab('results');
    } catch (error) {
        console.error('Error running analysis:', error);
        alert('Error running analysis: ' + error.message);
    }
}

function displayResults(results) {
    const resultsContent = document.getElementById('resultsContent');
    resultsContent.innerHTML = `
        <div class="results-summary">
            <h3>Projection Summary (${results.years.length} years)</h3>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <h4>Total Account Balance (Year 1)</h4>
                    <p class="metric-value">$${(results.total_balance || 0).toLocaleString()}</p>
                </div>
                <div class="metric-card">
                    <h4>Total Annual Income (Year 1)</h4>
                    <p class="metric-value">$${(results.total_income || 0).toLocaleString()}</p>
                </div>
                <div class="metric-card">
                    <h4>Total Annual Expenses (Year 1)</h4>
                    <p class="metric-value">$${(results.total_expenses || 0).toLocaleString()}</p>
                </div>
                <div class="metric-card">
                    <h4>Projected Taxes (Year 1)</h4>
                    <p class="metric-value">$${(results.total_taxes || 0).toLocaleString()}</p>
                </div>
            </div>
            
            <h3 style="margin-top: 2rem;">Recommended Conversion Strategy</h3>
            <div class="strategy-recommendation">
                <p>Based on your financial profile, consider converting <strong>$${(results.recommended_conversion || 0).toLocaleString()}</strong> annually to Roth.</p>
                <ul>
                    <li>This keeps you in the same tax bracket</li>
                    <li>Maximizes tax-free growth potential</li>
                    <li>Reduces future RMD burden</li>
                    <li>Provides tax diversification</li>
                </ul>
            </div>
            
            ${results.chart_balance ? `
                <h3 style="margin-top: 2rem;">Account Balance Projection</h3>
                <img src="data:image/png;base64,${results.chart_balance}" style="width: 100%; max-width: 600px; margin-top: 1rem;">
            ` : ''}
            
            ${results.chart_income ? `
                <h3 style="margin-top: 2rem;">Income vs Expenses</h3>
                <img src="data:image/png;base64,${results.chart_income}" style="width: 100%; max-width: 600px; margin-top: 1rem;">
            ` : ''}
        </div>
    `;
}

function downloadReport() {
    const clientData = JSON.parse(localStorage.getItem('clientData') || '{}');
    const reportText = `Roth Conversion Simulator Report
Generated: ${new Date().toLocaleDateString()}

Client: ${clientData.firstName} ${clientData.lastName}
Birth Year: ${clientData.birthYear}
Age: ${new Date().getFullYear() - clientData.birthYear}
State: ${clientData.state}
Filing Status: ${clientData.filingStatus}

Accounts:
${JSON.parse(localStorage.getItem('accounts') || '[]').map(a => 
    `  - ${a.name} (${a.type}): $${a.balance.toLocaleString()}`
).join('\n')}

Income Streams:
${JSON.parse(localStorage.getItem('incomeStreams') || '[]').map(i => 
    `  - ${i.source}: $${i.amount.toLocaleString()}/year (${i.type})`
).join('\n')}
`;
    
    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `roth-report-${Date.now()}.txt`;
    a.click();
}

// ============= International Tax Strategies =============
async function viewInternationalStrategies() {
    try {
        const response = await fetch('/api/international-strategies');
        const strategies = await response.json();
        
        let html = '<h3>International Tax Strategies</h3>';
        strategies.forEach(strategy => {
            html += `
                <div class="strategy-card">
                    <h4>${strategy.country}</h4>
                    <p>${strategy.description}</p>
                    <p><strong>Tax Rate:</strong> ${strategy.tax_rate}%</p>
                    <p><strong>Key Benefits:</strong></p>
                    <ul>
                        ${strategy.benefits.map(b => `<li>${b}</li>`).join('')}
                    </ul>
                </div>
            `;
        });
        
        document.getElementById('intlStrategiesContent').innerHTML = html;
    } catch (error) {
        console.error('Error loading international strategies:', error);
        document.getElementById('intlStrategiesContent').innerHTML = 
            '<p style="color: #f00;">Error loading strategies. Please try again.</p>';
    }
}

async function compareInternationalTaxes() {
    try {
        const response = await fetch('/api/international-comparison');
        const comparison = await response.json();
        
        let html = '<h3>International Tax Comparison</h3><table style="width: 100%; border-collapse: collapse;">';
        html += '<tr style="border-bottom: 2px solid #04a4ff;"><th style="padding: 1rem;">Country</th><th>Tax Rate</th><th>Estimated US Tax</th><th>Savings</th></tr>';
        
        comparison.forEach(row => {
            html += `<tr style="border-bottom: 1px solid #333;">
                <td style="padding: 0.5rem;">${row.country}</td>
                <td>${row.local_tax_rate}%</td>
                <td>$${row.us_tax.toLocaleString()}</td>
                <td style="color: #4f0;">$${row.savings.toLocaleString()}</td>
            </tr>`;
        });
        
        html += '</table>';
        document.getElementById('intlStrategiesContent').innerHTML = html;
    } catch (error) {
        console.error('Error comparing taxes:', error);
    }
}

// ============= Advanced Strategies =============
function calculateBackdoorRoth() {
    const backdoorAmount = parseFloat(document.getElementById('backdoorAmount').value) || 7000;
    const pretaxBalance = parseFloat(document.getElementById('pretaxIRABalance').value) || 0;
    
    const proRataPercent = pretaxBalance / (pretaxBalance + backdoorAmount);
    const taxableAmount = backdoorAmount * proRataPercent;
    const assumedTaxRate = 0.24;
    const estimatedTax = taxableAmount * assumedTaxRate;
    
    document.getElementById('backdroorResults').innerHTML = `
        <div class="result-box">
            <h4>Pro-Rata Rule Impact</h4>
            <p><strong>Contribution Amount:</strong> $${backdoorAmount.toLocaleString()}</p>
            <p><strong>Pre-Tax IRA Balance:</strong> $${pretaxBalance.toLocaleString()}</p>
            <p><strong>Taxable Portion:</strong> $${taxableAmount.toLocaleString()} (${(proRataPercent * 100).toFixed(1)}%)</p>
            <p style="color: #f00;"><strong>Estimated Tax at 24%:</strong> $${estimatedTax.toLocaleString()}</p>
            <p style="color: #4f0;"><strong>Tax-Free Roth Growth:</strong> $${(backdoorAmount - taxableAmount).toLocaleString()}</p>
        </div>
    `;
}

function calculateMegaBackdoor() {
    const salary = parseFloat(document.getElementById('megaSalary').value) || 0;
    const match = parseFloat(document.getElementById('megaMatch').value) || 0;
    
    const limit2024 = 69000;
    const employeeElective = 23500;
    const afterTax = limit2024 - employeeElective - match;
    
    document.getElementById('megaResults').innerHTML = `
        <div class="result-box">
            <h4>2024 Mega Backdoor Roth Capacity</h4>
            <p><strong>Annual Limit:</strong> $${limit2024.toLocaleString()}</p>
            <p><strong>- Employee Deferral:</strong> $${employeeElective.toLocaleString()}</p>
            <p><strong>- Employer Match:</strong> $${match.toLocaleString()}</p>
            <p style="color: #4f0;"><strong>= Maximum After-Tax Contribution:</strong> $${afterTax.toLocaleString()}</p>
            <p style="font-size: 0.9rem; color: #888; margin-top: 1rem;">Subject to plan availability and pro-rata considerations</p>
        </div>
    `;
}

function calculateSolo401k() {
    const seIncome = parseFloat(document.getElementById('solo401kIncome').value) || 0;
    
    // SE tax calculation
    const seTax = seIncome * 0.9235 * 0.153;
    const seDeduction = seTax / 2;
    const netSEIncome = seIncome - seDeduction;
    
    // Solo 401k limits for 2024
    const employeeDeferral = Math.min(netSEIncome * 0.25, 23500);
    const employerMatch = netSEIncome * 0.20;
    const totalContribution = employeeDeferral + employerMatch;
    const limit2024 = 69000;
    const maxContribution = Math.min(totalContribution, limit2024);
    
    document.getElementById('solo401kResults').innerHTML = `
        <div class="result-box">
            <h4>Solo 401(k) Maximum Contribution</h4>
            <p><strong>Self-Employment Income:</strong> $${seIncome.toLocaleString()}</p>
            <p><strong>- SE Tax (estimated):</strong> $${seTax.toLocaleString()}</p>
            <p><strong>Net Self-Employment Income:</strong> $${netSEIncome.toLocaleString()}</p>
            <p><strong>Employee Deferral (20% of net):</strong> $${employeeDeferral.toLocaleString()}</p>
            <p><strong>Employer Match (25% of net):</strong> $${employerMatch.toLocaleString()}</p>
            <p style="color: #4f0;"><strong>Total Max Contribution (2024 limit $69,000):</strong> $${maxContribution.toLocaleString()}</p>
        </div>
    `;
}

// ============= Utility Functions =============
function showHelp() {
    alert(`Roth Conversion Simulator - Help

This tool helps you optimize your retirement strategy by modeling Roth conversions.

TABS:
1. Client Info - Enter your personal details
2. Accounts - Add all retirement accounts
3. Income - List your income sources
4. Expenses - Set your annual spending
5. Settings - Configure analysis parameters
6. Results - Run analysis and view projections
7. International Tax - Explore global strategies
8. Advanced Strategies - Backdoor Roth, Solo 401k, etc.

TIPS:
- Fill in Client, Accounts, and Income before running analysis
- Use realistic growth rates (7% historical average)
- Consider your tax bracket when planning conversions
- International strategies are informational only

Questions? This is a planning tool, not financial advice.`);
}

function clearSession() {
    if (confirm('Clear all data and start fresh?')) {
        localStorage.clear();
        accounts = [];
        incomeStreams = [];
        displayAccounts();
        displayIncome();
        switchTab('client');
        alert('Session cleared!');
    }
}

// ============= Load Data on Page Load =============
document.addEventListener('DOMContentLoaded', () => {
    // Load saved data from localStorage
    const savedAccounts = localStorage.getItem('accounts');
    if (savedAccounts) {
        accounts = JSON.parse(savedAccounts);
        displayAccounts();
    }
    
    const savedIncome = localStorage.getItem('incomeStreams');
    if (savedIncome) {
        incomeStreams = JSON.parse(savedIncome);
        displayIncome();
    }
    
    const savedClient = localStorage.getItem('clientData');
    if (savedClient) {
        const client = JSON.parse(savedClient);
        document.getElementById('firstName').value = client.firstName;
        document.getElementById('lastName').value = client.lastName;
        document.getElementById('birthYear').value = client.birthYear;
        document.getElementById('maritalStatus').value = client.maritalStatus;
        if (client.spouseBirthYear) {
            document.getElementById('spouseBirthYear').value = client.spouseBirthYear;
            document.getElementById('spouseYearGroup').style.display = 'block';
        }
        document.getElementById('state').value = client.state;
        document.getElementById('filingStatus').value = client.filingStatus;
    }
    
    const savedExpenses = localStorage.getItem('expenses');
    if (savedExpenses) {
        const exp = JSON.parse(savedExpenses);
        document.getElementById('basicExpenses').value = exp.basic;
        document.getElementById('healthExpenses').value = exp.health;
        document.getElementById('travelExpenses').value = exp.travel;
        document.getElementById('inflationRate').value = exp.inflation;
    }
    
    const savedSettings = localStorage.getItem('settings');
    if (savedSettings) {
        const sets = JSON.parse(savedSettings);
        document.getElementById('startYear').value = sets.startYear;
        document.getElementById('endYear').value = sets.endYear;
        document.getElementById('federalRate').value = sets.federalRate;
        document.getElementById('stateRate').value = sets.stateRate;
        document.getElementById('defaultGrowth').value = sets.defaultGrowth;
        document.getElementById('withdrawalSequence').value = sets.withdrawalSequence;
        document.getElementById('optimizationGoal').value = sets.optimizationGoal;
    }
});
