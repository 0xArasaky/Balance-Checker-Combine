let filesList = [];
let currentFile = null;
let currentData = null;
let scrambleInstances = [];
let isFirstLoad = true;

const dataSelectorBtn = document.getElementById('dataSelectorBtn');
const dataDropdown = document.getElementById('dataDropdown');
const dropdownList = document.getElementById('dropdownList');
const currentDate = document.getElementById('currentDate');
const currentBalance = document.getElementById('currentBalance');

function formatBalance(balance) {
    return `$${balance.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    })}`;
}

function animateBalance(element, targetValue, duration = 720) {
    const startTime = performance.now();
    const startValue = 0;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        const eased = 1 - Math.pow(1 - progress, 3);

        const currentValue = Math.round(startValue + (targetValue - startValue) * eased);
        element.textContent = formatBalance(currentValue);

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {

            element.textContent = formatBalance(targetValue);
        }
    }

    requestAnimationFrame(update);
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}.${month}.${year} ${hours}:${minutes}`;
}

async function loadFilesList() {
    try {

        const response = await fetch('/api/files');
        if (!response.ok) {
            throw new Error('Не удалось загрузить список файлов');
        }

        const data = await response.json();
        filesList = data.files;

        if (filesList.length > 0) {
            currentFile = filesList[0];
            updateCurrentDisplay();
            populateDropdown();

            loadAnalysisData();
        } else {
            currentDate.textContent = 'No data';
            currentBalance.textContent = '$0';
        }
    } catch (error) {
        console.error('Error loading files list:', error);
        currentDate.textContent = 'Loading error';
        currentBalance.textContent = '$0';
    }
}

function updateCurrentDisplay() {
    if (currentFile) {
        currentDate.textContent = formatDate(currentFile.timestamp);

        currentBalance.textContent = '$0';
        currentBalance.dataset.targetValue = currentFile.total_balance;
    }
}

function populateDropdown() {
    dropdownList.innerHTML = '';

    filesList.forEach((file, index) => {
        const item = document.createElement('button');
        item.className = 'dropdown-item';
        item.dataset.filename = file.filename;

        if (currentFile && file.filename === currentFile.filename) {
            item.classList.add('selected');
        }

        const dateSpan = document.createElement('span');
        dateSpan.className = 'dropdown-item-date';
        dateSpan.textContent = formatDate(file.timestamp);

        const balanceSpan = document.createElement('span');
        balanceSpan.className = 'dropdown-item-balance';
        balanceSpan.textContent = formatBalance(file.total_balance);

        item.appendChild(dateSpan);
        item.appendChild(balanceSpan);

        item.addEventListener('click', (e) => {
            e.stopPropagation();
            selectFile(file);
        });

        dropdownList.appendChild(item);
    });
}

function selectFile(file) {
    currentFile = file;
    updateCurrentDisplay();

    const items = dropdownList.querySelectorAll('.dropdown-item');
    items.forEach(item => {
        if (item.dataset.filename === file.filename) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });

    toggleDropdown();

    loadAnalysisData(file.filename);
}

function toggleDropdown() {
    const isActive = dataDropdown.classList.toggle('active');
    dataSelectorBtn.classList.toggle('active', isActive);
}

document.addEventListener('click', (e) => {
    if (!dataSelectorBtn.contains(e.target) && !dataDropdown.contains(e.target)) {
        dataDropdown.classList.remove('active');
        dataSelectorBtn.classList.remove('active');
    }
});

dataSelectorBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDropdown();
});

async function loadAnalysisData(filename = null) {
    try {

        const url = filename ? `data/${filename}` : '/api/latest';
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error('Failed to load analysis data');
        }

        currentData = await response.json();
        displayTotalStats();
    } catch (error) {
        console.error('Error loading analysis data:', error);
    }
}

function displayTotalStats() {
    if (!currentData || !currentData.total_stats) {
        return;
    }

    displayCategories();
    displayTokens();
    displayWalletGroups();

    waitForCompleteRender().then(() => {
        if (isFirstLoad) {
            hideLoadingOverlay();
        } else {

            startAllAnimations();
        }
    });
}

function waitForCompleteRender() {
    return new Promise((resolve) => {

        waitForElementsReady().then(() => {

            showAllSquaresInstantly();

            requestAnimationFrame(() => {
                requestAnimationFrame(() => {

                    waitForBrowserIdle().then(() => {
                        resolve();
                    });
                });
            });
        });
    });
}

function showAllSquaresInstantly() {

    const allSquares = document.querySelectorAll('.progress-square');
    allSquares.forEach(square => {
        square.classList.remove('visible', 'animate');
        square.style.animationDelay = '';
    });

    const visibleSquares = document.querySelectorAll('.progress-bar .progress-square[data-visible="true"]');
    visibleSquares.forEach(square => {
        square.classList.add('visible');
    });
}

function startAllAnimations() {

    const allSquares = document.querySelectorAll('.progress-square');
    allSquares.forEach(square => {
        square.classList.remove('visible', 'animate');
        square.style.animationDelay = '';
    });

    requestAnimationFrame(() => {
        animateProgressBarsCSS();

        animateBalances();
        scrambleInstances.forEach(instance => instance.trigger());
    });
}

function waitForElementsReady() {
    return new Promise((resolve) => {
        const checkReady = () => {

            const categoriesExist = document.querySelectorAll('.category-item').length > 0;
            const tokensExist = document.querySelectorAll('.token-item').length > 0;
            const progressBarsExist = document.querySelectorAll('.progress-square').length > 0;

            if (categoriesExist && tokensExist && progressBarsExist) {
                resolve();
            } else {

                setTimeout(checkReady, 10);
            }
        };

        checkReady();
    });
}

function waitForBrowserIdle() {
    return new Promise((resolve) => {

        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {

                requestAnimationFrame(() => {
                    resolve();
                });
            }, { timeout: 500 });
        } else {

            setTimeout(() => {
                requestAnimationFrame(() => {
                    resolve();
                });
            }, 100);
        }
    });
}

function displayCategories() {
    const categoriesList = document.getElementById('categoriesList');
    const categories = currentData.total_stats.categories;
    const totalBalance = currentData.metadata.total_balance;

    const categoryOrder = ['EVM', 'SOL', 'BTC', 'APT', 'OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];

    const subcategoryNames = {
        chains: 'Chains',
        defi_other: 'DeFi & Other',
        polymarket_positions: 'Polymarket Positions',
        polymarket_total: 'Polymarket Total',
        hyperliquid: 'Hyperliquid Total',
        lighter: 'Lighter',
        tokens: 'Tokens',
        defi: 'DeFi',
        btc: 'BTC',
        runes: 'Runes',
        inscriptions: 'Inscriptions',
        apt: 'APT',
        other_tokens: 'Other Tokens',
        staked_apt: 'Staked APT'
    };

    categoriesList.innerHTML = '';

    categoryOrder.forEach(categoryName => {
        if (!categories[categoryName]) return;

        const category = categories[categoryName];
        const categoryPercent = (category.total / totalBalance) * 100;

        const categoryItem = document.createElement('div');
        categoryItem.className = 'category-item';

        const mainRow = document.createElement('div');
        mainRow.className = 'category-main';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'category-name';
        nameSpan.textContent = categoryName;

        const progressBar = createProgressBar(categoryPercent, false);

        const balanceSpan = document.createElement('span');
        balanceSpan.className = 'category-balance';
        balanceSpan.textContent = '$0';
        balanceSpan.dataset.targetValue = category.total;

        mainRow.appendChild(nameSpan);
        mainRow.appendChild(progressBar);
        mainRow.appendChild(balanceSpan);

        categoryItem.appendChild(mainRow);

        const subcategories = getSubcategories(category, categoryName);
        if (subcategories.length > 0) {

            subcategories.sort((a, b) => b.value - a.value);

            subcategories.forEach(sub => {

                const subPercent = (sub.value / category.total) * categoryPercent;

                const subRow = document.createElement('div');
                subRow.className = 'subcategory-item';

                const subName = document.createElement('span');
                subName.className = 'subcategory-name';
                subName.textContent = `└─ ${sub.name}`;

                const subProgressBar = createProgressBar(subPercent, true);

                const subBalance = document.createElement('span');
                subBalance.className = 'subcategory-balance';
                subBalance.textContent = '$0';
                subBalance.dataset.targetValue = sub.value;

                subRow.appendChild(subName);
                subRow.appendChild(subProgressBar);
                subRow.appendChild(subBalance);

                categoryItem.appendChild(subRow);
            });
        }

        categoriesList.appendChild(categoryItem);
    });
}

function getSubcategories(category, categoryName) {
    const subcategories = [];
    const excludeKeys = ['total'];

    for (const key in category) {
        if (excludeKeys.includes(key)) continue;

        const subcategoryNames = {
            chains: 'Chains',
            defi_other: 'DeFi & Other',
            polymarket_positions: 'Polymarket Positions',
            polymarket_total: 'Polymarket Total',
            hyperliquid: 'Hyperliquid Total',
            lighter: 'Lighter',
            tokens: 'Tokens',
            defi: 'DeFi',
            btc: 'BTC',
            runes: 'Runes',
            inscriptions: 'Inscriptions',
            apt: 'APT',
            other_tokens: 'Other Tokens',
            staked_apt: 'Staked APT'
        };

        subcategories.push({
            key: key,
            name: subcategoryNames[key] || key,
            value: category[key]
        });
    }

    return subcategories;
}

function displayTokens() {
    const tokensList = document.getElementById('tokensList');
    const tokens = currentData.total_stats.tokens;
    const totalBalance = currentData.metadata.total_balance;

    tokensList.innerHTML = '';

    for (const tokenName in tokens) {
        const tokenValue = tokens[tokenName];
        const tokenPercent = (tokenValue / totalBalance) * 100;

        const tokenItem = document.createElement('div');
        tokenItem.className = 'token-item';

        const name = document.createElement('span');
        name.className = 'token-name';
        name.textContent = tokenName;

        const progressBar = createProgressBar(tokenPercent, false);

        const balance = document.createElement('span');
        balance.className = 'token-balance';
        balance.textContent = '$0';
        balance.dataset.targetValue = tokenValue;

        tokenItem.appendChild(name);
        tokenItem.appendChild(progressBar);
        tokenItem.appendChild(balance);

        tokensList.appendChild(tokenItem);
    }
}

function displayWalletGroups() {
    const walletGroupsSection = document.getElementById('walletGroupsSection');

    if (!currentData || !currentData.categories) {
        walletGroupsSection.innerHTML = '';
        return;
    }

    walletGroupsSection.innerHTML = '';

    const categoryOrder = ['EVM', 'SOL', 'BTC', 'APT', 'OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];

    const exchangeCategories = ['OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];

    categoryOrder.forEach(categoryName => {
        if (!currentData.categories[categoryName] || !currentData.categories[categoryName].items) {
            return;
        }

        const items = currentData.categories[categoryName].items;
        const isExchange = exchangeCategories.includes(categoryName);

        const groupedItems = {};
        items.forEach(item => {
            const groupName = item.group || 'Unknown';
            if (!groupedItems[groupName]) {
                groupedItems[groupName] = [];
            }
            groupedItems[groupName].push(item);
        });

        for (const groupName in groupedItems) {
            const groupItems = groupedItems[groupName];

            const groupDiv = document.createElement('div');
            groupDiv.className = 'wallet-group';

            const groupTitle = document.createElement('h2');
            groupTitle.className = 'wallet-group-title';
            groupTitle.textContent = `${categoryName} - ${groupName}`;
            groupDiv.appendChild(groupTitle);

            const tableHeader = document.createElement('div');
            tableHeader.className = 'wallet-table-header';

            if (isExchange) {

                tableHeader.innerHTML = `
                    <span class="wallet-header-name">Name</span>
                    <span class="wallet-header-address">API Key</span>
                    <span class="wallet-header-balance">Balance</span>
                `;
            } else {

                tableHeader.innerHTML = `
                    <span class="wallet-header-name">Name</span>
                    <span class="wallet-header-address">Address</span>
                    <span class="wallet-header-balance">Balance</span>
                `;
            }
            groupDiv.appendChild(tableHeader);

            groupItems.forEach(item => {
                const itemRow = createWalletRow(item, categoryName, isExchange);
                groupDiv.appendChild(itemRow);
            });

            walletGroupsSection.appendChild(groupDiv);
        }
    });
}

function createWalletRow(wallet, categoryName, isExchange = false) {
    const walletRow = document.createElement('div');
    walletRow.className = 'wallet-row';

    let displayName = wallet.name;
    if (displayName.length > 16) {
        displayName = displayName.substring(0, 13) + '...';
    }

    const walletRowMain = document.createElement('div');
    walletRowMain.className = 'wallet-row-main';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'wallet-name';
    nameSpan.textContent = displayName;

    const addressSpan = document.createElement('span');
    addressSpan.className = 'wallet-address';

    if (isExchange) {

        addressSpan.textContent = wallet.api_key_last4 ? `****${wallet.api_key_last4}` : 'N/A';
    } else {

        addressSpan.textContent = wallet.address || 'N/A';
    }

    const balanceSpan = document.createElement('span');
    balanceSpan.className = 'wallet-total-balance';
    balanceSpan.textContent = '$0';
    balanceSpan.dataset.targetValue = wallet.balances.total;

    walletRowMain.appendChild(nameSpan);
    walletRowMain.appendChild(addressSpan);
    walletRowMain.appendChild(balanceSpan);
    walletRow.appendChild(walletRowMain);

    const walletDetails = createWalletDetails(wallet, categoryName);
    walletRow.appendChild(walletDetails);

    walletRowMain.addEventListener('click', () => {
        const wasExpanded = walletRow.classList.contains('expanded');
        walletRow.classList.toggle('expanded');

        if (!wasExpanded) {

            setTimeout(() => {
                animateWalletDetails(walletRow);
            }, 10);
        }
    });

    return walletRow;
}

function createWalletDetails(wallet, categoryName) {
    const walletDetails = document.createElement('div');
    walletDetails.className = 'wallet-details';

    const balances = wallet.balances;
    const tokens = wallet.tokens || {};
    const totalBalance = balances.total;

    const addTokens = (parentLabel = null) => {
        if (Object.keys(tokens).length === 0) return;

        const otherEntry = Object.entries(tokens).find(([name]) => name === 'Other');
        const regularTokens = Object.entries(tokens).filter(([name]) => name !== 'Other');

        const sortedTokens = regularTokens.sort((a, b) => b[1] - a[1]);

        sortedTokens.forEach(([tokenName, tokenValue]) => {
            const prefix = parentLabel ? '└─ ' : '';
            const tokenItem = createDetailItem(`${prefix}${tokenName}`, tokenValue, totalBalance, true);
            walletDetails.appendChild(tokenItem);
        });

        if (otherEntry) {
            const [tokenName, tokenValue] = otherEntry;
            const prefix = parentLabel ? '└─ ' : '';
            const tokenItem = createDetailItem(`${prefix}${tokenName}`, tokenValue, totalBalance, true);
            walletDetails.appendChild(tokenItem);
        }
    };

    if (categoryName === 'EVM') {

        if (balances.chains > 0) {
            const chainsItem = createDetailItem('Chains', balances.chains, totalBalance, false);
            walletDetails.appendChild(chainsItem);
            addTokens('Chains');
        }

        if (balances.defi_other > 0) {
            const defiItem = createDetailItem('DeFi & Other', balances.defi_other, totalBalance, false);
            walletDetails.appendChild(defiItem);
        }

        if (balances.polymarket_positions > 0) {
            const polyPosItem = createDetailItem('Polymarket Positions', balances.polymarket_positions, totalBalance, false);
            walletDetails.appendChild(polyPosItem);
        }

        if (balances.polymarket_total > 0) {
            const polyTotalItem = createDetailItem('Polymarket Total', balances.polymarket_total, totalBalance, false);
            walletDetails.appendChild(polyTotalItem);
        }

        if (balances.hyperliquid > 0) {
            const hyperItem = createDetailItem('Hyperliquid Total', balances.hyperliquid, totalBalance, false);
            walletDetails.appendChild(hyperItem);
        }

        if (balances.lighter > 0) {
            const lighterItem = createDetailItem('Lighter', balances.lighter, totalBalance, false);
            walletDetails.appendChild(lighterItem);
        }
    }

    else if (categoryName === 'SOL') {

        if (balances.tokens > 0) {
            const tokensItem = createDetailItem('Tokens', balances.tokens, totalBalance, false);
            walletDetails.appendChild(tokensItem);
            addTokens('Tokens');
        }

        if (balances.defi > 0) {
            const defiItem = createDetailItem('DeFi', balances.defi, totalBalance, false);
            walletDetails.appendChild(defiItem);
        }
    }

    else if (categoryName === 'BTC') {

        if (balances.btc > 0) {
            const btcItem = createDetailItem('BTC', balances.btc, totalBalance, false);
            walletDetails.appendChild(btcItem);
        }

        if (balances.runes > 0) {
            const runesItem = createDetailItem('Runes', balances.runes, totalBalance, false);
            walletDetails.appendChild(runesItem);
        }

        if (balances.inscriptions > 0) {
            const inscrItem = createDetailItem('Inscriptions', balances.inscriptions, totalBalance, false);
            walletDetails.appendChild(inscrItem);
        }
    }

    else if (categoryName === 'APT') {

        if (balances.apt > 0) {
            const aptItem = createDetailItem('APT', balances.apt, totalBalance, false);
            walletDetails.appendChild(aptItem);
        }

        if (balances.staked_apt > 0) {
            const stakedItem = createDetailItem('Staked APT', balances.staked_apt, totalBalance, false);
            walletDetails.appendChild(stakedItem);
        }

        if (Object.keys(tokens).length > 0) {
            const otherEntry = Object.entries(tokens).find(([name]) => name === 'Other');
            const regularTokens = Object.entries(tokens).filter(([name]) => name !== 'APT' && name !== 'Other');

            const sortedTokens = regularTokens.sort((a, b) => b[1] - a[1]);

            sortedTokens.forEach(([tokenName, tokenValue]) => {
                const tokenItem = createDetailItem(tokenName, tokenValue, totalBalance, false);
                walletDetails.appendChild(tokenItem);
            });

            if (otherEntry) {
                const [tokenName, tokenValue] = otherEntry;
                const tokenItem = createDetailItem(tokenName, tokenValue, totalBalance, false);
                walletDetails.appendChild(tokenItem);
            }
        }
    }

    else {

        addTokens(null);
    }

    return walletDetails;
}

function createDetailItem(name, value, totalBalance, isToken) {
    const detailItem = document.createElement('div');
    detailItem.className = 'wallet-detail-item';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'wallet-detail-name';
    if (isToken) {
        nameSpan.classList.add('token');
    }
    nameSpan.textContent = name;

    const percent = (value / totalBalance) * 100;
    const progressBar = createWalletDetailBar(percent, isToken);

    const balanceSpan = document.createElement('span');
    balanceSpan.className = 'wallet-detail-balance';
    if (isToken) {
        balanceSpan.classList.add('token');
    }
    balanceSpan.textContent = '$0';
    balanceSpan.dataset.targetValue = value;

    detailItem.appendChild(nameSpan);
    detailItem.appendChild(progressBar);
    detailItem.appendChild(balanceSpan);

    return detailItem;
}

function createWalletDetailBar(percent, isToken) {
    const TOTAL_SQUARES = 130;
    let squaresToShow = Math.round((percent / 100) * TOTAL_SQUARES);

    if (squaresToShow === 0) {
        squaresToShow = 1;
    }

    const progressBar = document.createElement('div');
    progressBar.className = 'wallet-detail-bar';

    for (let i = 0; i < squaresToShow; i++) {
        const square = document.createElement('div');
        square.className = 'progress-square';

        if (isToken) {
            square.classList.add('subcategory');
        }

        square.dataset.visible = 'true';
        square.dataset.index = i;

        progressBar.appendChild(square);
    }

    return progressBar;
}

function createProgressBar(percent, isSubcategory) {
    const TOTAL_SQUARES = 144;

    let squaresToShow = Math.round((percent / 100) * TOTAL_SQUARES);

    if (squaresToShow === 0) {
        squaresToShow = 1;
    }

    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';

    for (let i = 0; i < squaresToShow; i++) {
        const square = document.createElement('div');
        square.className = 'progress-square';

        if (isSubcategory) {
            square.classList.add('subcategory');
        }

        square.dataset.visible = 'true';
        square.dataset.index = i;

        progressBar.appendChild(square);
    }

    return progressBar;
}

function animateProgressBarsCSS() {
    const progressBars = document.querySelectorAll('.progress-bar');

    progressBars.forEach(bar => {
        const squares = bar.querySelectorAll('.progress-square[data-visible="true"]');

        squares.forEach((square, index) => {

            square.style.animationDelay = `${index * 5}ms`;

            square.classList.add('animate');
        });
    });
}

function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar, .wallet-detail-bar');

    progressBars.forEach(bar => {
        const squares = bar.querySelectorAll('.progress-square[data-visible="true"]');

        squares.forEach((square, index) => {

            setTimeout(() => {
                square.classList.add('visible');
            }, index * 5);
        });
    });

    animateBalances();
}

function animateBalances() {

    const duration = 720;

    if (currentBalance.dataset.targetValue) {
        const targetValue = parseFloat(currentBalance.dataset.targetValue);
        currentBalance.textContent = '$0';
        animateBalance(currentBalance, targetValue, duration);
    }

    document.querySelectorAll('.category-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    document.querySelectorAll('.subcategory-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    document.querySelectorAll('.token-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    document.querySelectorAll('.wallet-detail-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    document.querySelectorAll('.wallet-total-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });
}

function animateWalletDetails(walletRow) {
    const duration = 720;

    const detailBars = walletRow.querySelectorAll('.wallet-detail-bar');
    detailBars.forEach(bar => {
        const squares = bar.querySelectorAll('.progress-square[data-visible="true"]');
        squares.forEach((square, index) => {

            square.classList.remove('visible');

            setTimeout(() => {
                square.classList.add('visible');
            }, index * 5);
        });
    });

    const detailBalances = walletRow.querySelectorAll('.wallet-detail-balance');
    detailBalances.forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });
}

class ScrambleText {
    constructor(element, options = {}) {
        this.element = element;

        this.originalHTML = element.innerHTML;
        this.originalText = element.dataset.text || element.textContent.replace(/\n/g, '');

        const isNumericVersion = /^\d+\.\d+\.\d+$/.test(this.originalText.trim());
        if (isNumericVersion) {
            this.chars = '0123456789';

            this.frameRate = options.frameRate || 30;
            this.iterations = options.iterations || 4;
            this.scrambleCount = options.scrambleCount || 2;
        } else {
            this.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';

            this.frameRate = options.frameRate || 16;
            this.iterations = options.iterations || 2;
            this.scrambleCount = options.scrambleCount || 20;
        }

        this.frameRequest = null;
        this.frame = 0;
        this.isAnimating = false;
        this.lastAnimationTime = 0;
        this.cooldown = 5000;

        this.element.addEventListener('mouseenter', () => this.scrambleWithCooldown());
    }

    scrambleWithCooldown() {
        const now = Date.now();
        if (now - this.lastAnimationTime < this.cooldown) {
            return;
        }
        this.scramble();
    }

    trigger() {

        this.scramble();
    }

    getRandomChar(originalChar) {

        const isUpperCase = originalChar === originalChar.toUpperCase();

        let availableChars;
        if (isUpperCase) {
            availableChars = this.chars.split('').filter(c => c === c.toUpperCase()).join('');
        } else {
            availableChars = this.chars.split('').filter(c => c === c.toLowerCase() && c !== c.toUpperCase()).join('');
        }

        if (availableChars.length === 0) {
            availableChars = this.chars;
        }

        return availableChars[Math.floor(Math.random() * availableChars.length)];
    }

    scramble() {
        if (this.isAnimating) return;

        this.isAnimating = true;
        this.lastAnimationTime = Date.now();
        this.frame = 0;

        const animate = () => {
            let output = '';
            let revealedCount = 0;
            let allComplete = true;

            const shouldReveal = Math.floor(this.frame / this.iterations);

            for (let i = 0; i < this.originalText.length; i++) {
                const char = this.originalText[i];

                if (this.originalHTML.includes('<br>') && i === 15) {
                    output += '<br>';
                }

                if (char === ' ' || char === '.') {
                    output += char;
                    continue;
                }

                if (revealedCount < shouldReveal) {

                    output += char;
                    revealedCount++;
                } else if (revealedCount >= shouldReveal && revealedCount < shouldReveal + this.scrambleCount) {

                    const randomChar = this.getRandomChar(char);
                    output += `<span class="scramble-char">${randomChar}</span>`;
                    revealedCount++;
                    allComplete = false;
                } else {

                    allComplete = false;
                    break;
                }
            }

            this.element.innerHTML = output;

            if (!allComplete) {
                this.frame++;
                this.frameRequest = setTimeout(animate, this.frameRate);
            } else {

                this.element.innerHTML = this.originalHTML;
                this.isAnimating = false;
            }
        };

        animate();
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');

    overlay.classList.add('hidden');

    setTimeout(() => {
        startAllAnimations();
        isFirstLoad = false;
    }, 100);
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Balance Checker Combine загружен');

    document.querySelectorAll('.scramble-text').forEach(element => {
        const instance = new ScrambleText(element);
        scrambleInstances.push(instance);
    });

    loadFilesList();
});
