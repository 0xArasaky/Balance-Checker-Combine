// Balance Checker Combine - Main JavaScript

// Глобальные переменные
let filesList = [];
let currentFile = null;
let currentData = null;
let scrambleInstances = []; // Инстансы ScrambleText для управления
let isFirstLoad = true; // Флаг первой загрузки
let activeHistoryRange = '30d'; // Активный диапазон графика истории
let historyChartData = [];
let historyChartAnimationFrame = null;

// Элементы DOM
const dataSelectorBtn = document.getElementById('dataSelectorBtn');
const dataDropdown = document.getElementById('dataDropdown');
const dropdownList = document.getElementById('dropdownList');
const currentDate = document.getElementById('currentDate');
const currentBalance = document.getElementById('currentBalance');
const historySection = document.getElementById('historySection');
const historyCanvas = document.getElementById('historyCanvas');
const historyChartTooltip = document.getElementById('historyChartTooltip');
const historyChartDot = document.getElementById('historyChartDot');
const historyRangeToggle = document.getElementById('historyRangeToggle');
const historyRangeSlider = document.getElementById('historyRangeSlider');
const historyRangeButtons = document.querySelectorAll('.balance-history-range__btn');
const topSourcesSection = document.getElementById('topSourcesSection');
const topSourcesList = document.getElementById('topSourcesList');

const HISTORY_RANGE_DAYS = {
    '7d': 7,
    '30d': 30,
    '1y': 365,
    all: null
};
const HISTORY_DAY_MS = 24 * 60 * 60 * 1000;

// Форматирование баланса
function formatBalance(balance) {
    return `$${balance.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    })}`;
}

// Анимация баланса от 0 до целевого значения
function animateBalance(element, targetValue, duration = 720) {
    const startTime = performance.now();
    const startValue = 0;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function для плавности (easeOutCubic)
        const eased = 1 - Math.pow(1 - progress, 3);

        const currentValue = Math.round(startValue + (targetValue - startValue) * eased);
        element.textContent = formatBalance(currentValue);

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            // Финальное значение для точности
            element.textContent = formatBalance(targetValue);
        }
    }

    requestAnimationFrame(update);
}

// Форматирование даты
function formatDate(timestamp) {
    const normalizedTimestamp = typeof timestamp === 'string'
        ? timestamp.replace(' ', 'T')
        : timestamp;
    const date = new Date(normalizedTimestamp);

    if (Number.isNaN(date.getTime())) {
        return timestamp || 'No date';
    }

    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}.${month}.${year} ${hours}:${minutes}`;
}

// Короткая дата для подписей графика
function formatShortDate(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = String(date.getFullYear()).slice(-2);

    return `${day}.${month}.${year}`;
}

// Парсинг timestamp из files_list.json
function parseHistoryDate(timestamp) {
    const normalizedTimestamp = typeof timestamp === 'string'
        ? timestamp.replace(' ', 'T')
        : timestamp;
    const date = new Date(normalizedTimestamp);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}

// Загрузка списка файлов
async function loadFilesList() {
    try {
        const response = await fetch('data/files_list.json', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('Не удалось загрузить список файлов');
        }

        const data = await response.json();
        filesList = data.files || [];

        // Загружаем последний файл (первый в списке, т.к. сервер сортирует по убыванию даты)
        if (filesList.length > 0) {
            currentFile = filesList[0];
            updateCurrentDisplay();
            populateDropdown();
            displayHistoryChart();
            loadAnalysisData(currentFile.filename);
        } else {
            currentDate.textContent = 'No data';
            currentBalance.textContent = '$0';
        }
    } catch (error) {
        console.error('Error loading files list:', error);
        await loadLatestAnalysisFallback();
    }
}

// Fallback: если список файлов недоступен, показываем последний скан напрямую
async function loadLatestAnalysisFallback() {
    try {
        const response = await fetch('data/latest.json', { cache: 'no-store' });
        if (!response.ok) {
            throw new Error('Не удалось загрузить latest.json');
        }

        currentData = await response.json();
        currentFile = {
            filename: 'latest.json',
            timestamp: currentData.metadata.timestamp_readable || currentData.metadata.timestamp,
            total_balance: currentData.metadata.total_balance || 0
        };
        filesList = [currentFile];

        updateCurrentDisplay();
        populateDropdown();
        displayHistoryChart();
        displayTotalStats();
    } catch (fallbackError) {
        console.error('Error loading latest analysis fallback:', fallbackError);
        currentDate.textContent = 'Loading error';
        currentBalance.textContent = '$0';
    }
}

// Обновление отображения текущего файла
function updateCurrentDisplay() {
    if (currentFile) {
        currentDate.textContent = formatDate(currentFile.timestamp);
        // Сначала показываем $0, потом анимация запустится
        currentBalance.textContent = '$0';
        currentBalance.dataset.targetValue = currentFile.total_balance;
    }
}

// Заполнение выпадающего списка
function populateDropdown() {
    dropdownList.innerHTML = '';

    filesList.forEach((file, index) => {
        const item = document.createElement('button');
        item.className = 'dropdown-item';
        item.dataset.filename = file.filename;

        // Добавляем класс selected для текущего файла
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

        // Обработчик клика
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            selectFile(file);
        });

        dropdownList.appendChild(item);
    });
}

// Получение точек истории баланса
function getHistoryPoints() {
    return filesList
        .map(file => {
            const date = parseHistoryDate(file.timestamp);
            const balance = Number(file.total_balance || 0);

            return {
                filename: file.filename,
                date,
                balance
            };
        })
        .filter(point => {
            if (!point.date || !Number.isFinite(point.balance)) {
                return false;
            }

            // Демонстрационный пример не должен ломать масштаб реальной истории.
            return point.filename !== 'balance_2000-01-01_00-00-00.json';
        })
        .sort((a, b) => a.date - b.date);
}

// Фильтрация точек истории по активному диапазону
function getVisibleHistoryPoints(points) {
    const rangeDays = HISTORY_RANGE_DAYS[activeHistoryRange];

    if (!rangeDays || points.length === 0) {
        return points;
    }

    const latestTime = points[points.length - 1].date.getTime();
    const minTime = latestTime - (rangeDays * HISTORY_DAY_MS);

    return points.filter(point => point.date.getTime() >= minTime);
}

// Обновление активной кнопки диапазона
function updateHistoryRangeButtons() {
    historyRangeButtons.forEach(button => {
        button.classList.toggle('balance-history-range__btn--active', button.dataset.range === activeHistoryRange);
    });
}

// Перемещение slider-а диапазона как в PolyEarn
function moveHistoryRangeSlider(button) {
    if (!historyRangeSlider || !historyRangeToggle || !button) {
        return;
    }

    const selectorRect = historyRangeToggle.getBoundingClientRect();
    const buttonRect = button.getBoundingClientRect();
    historyRangeSlider.style.left = `${buttonRect.left - selectorRect.left}px`;
    historyRangeSlider.style.width = `${buttonRect.width}px`;
}

function getActiveHistoryRangeButton() {
    const activeButton = document.querySelector(`.balance-history-range__btn[data-range="${activeHistoryRange}"]`);
    return activeButton || document.querySelector('.balance-history-range__btn--active');
}

function initHistoryRangeSlider() {
    const activeButton = getActiveHistoryRangeButton();
    if (!activeButton || !historyRangeSlider) {
        return;
    }

    historyRangeSlider.style.transition = 'none';
    moveHistoryRangeSlider(activeButton);
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            historyRangeSlider.style.transition = 'left 0.25s ease, width 0.25s ease';
        });
    });
}

function syncHistoryRangeControls() {
    updateHistoryRangeButtons();

    const activeButton = getActiveHistoryRangeButton();
    if (!activeButton) {
        return;
    }

    if (!historyRangeSlider || !historyRangeSlider.style.width) {
        initHistoryRangeSlider();
        return;
    }

    moveHistoryRangeSlider(activeButton);
}

// Отображение графика истории
function displayHistoryChart(animate = true) {
    if (!historySection || !historyCanvas) {
        return;
    }

    const allPoints = getHistoryPoints();

    if (allPoints.length <= 7) {
        historySection.hidden = true;
        historyChartData = [];
        historySection.classList.remove('balance-history--loaded');
        return;
    }

    const points = getVisibleHistoryPoints(allPoints);
    historySection.hidden = false;
    syncHistoryRangeControls();
    renderHistoryChart(points, animate);
}

function getHistoryCanvasMetrics(canvas) {
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    return {
        ctx,
        width: rect.width,
        height: rect.height,
        padding: { top: 10, right: 0, bottom: 10, left: 0 }
    };
}

function getHistoryChartRange(values) {
    const numericValues = values
        .map(value => Number(value))
        .filter(value => Number.isFinite(value));

    if (numericValues.length === 0) {
        return { min: 0, max: 1 };
    }

    const minValue = Math.min(...numericValues);
    const maxValue = Math.max(...numericValues, 1);

    if (activeHistoryRange === 'all' || minValue <= 0) {
        return { min: 0, max: Math.max(maxValue * 1.05, 1) };
    }

    const span = Math.max(maxValue - minValue, maxValue * 0.01, 1);
    const padding = span * 0.5;

    return {
        min: Math.max(0, minValue - padding),
        max: maxValue + padding
    };
}

function getHistoryChartY(value, range, padding, chartHeight) {
    const span = Math.max(range.max - range.min, 1);
    return padding.top + chartHeight - (((value - range.min) / span) * chartHeight);
}

function getHistoryChartTimeDomain(points) {
    if (!points || points.length === 0) {
        return { minTime: 0, maxTime: 1 };
    }

    const latestTime = points[points.length - 1].date.getTime();
    const maxTime = Number.isFinite(latestTime) ? latestTime : Date.now();
    const rangeDays = HISTORY_RANGE_DAYS[activeHistoryRange];
    let minTime = rangeDays
        ? maxTime - (rangeDays * HISTORY_DAY_MS)
        : points[0].date.getTime();

    if (!Number.isFinite(minTime) || minTime >= maxTime) {
        minTime = maxTime - HISTORY_DAY_MS;
    }

    return { minTime, maxTime };
}

function getHistoryChartX(point, timeDomain, padding, chartWidth) {
    const pointTime = point.date.getTime();
    const span = Math.max(timeDomain.maxTime - timeDomain.minTime, 1);
    const normalized = Math.max(0, Math.min(1, (pointTime - timeDomain.minTime) / span));

    return padding.left + (normalized * chartWidth);
}

function drawHistoryGrid(ctx, width, height, padding, range, progress) {
    const chartHeight = height - padding.top - padding.bottom;
    const gridLines = 4;
    const alpha = Math.min(progress * 2, 1);

    for (let i = 0; i <= gridLines; i++) {
        const y = padding.top + (chartHeight * i / gridLines);

        ctx.strokeStyle = `rgba(21, 21, 21, ${0.9 * alpha})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
    }
}

function drawHistoryChart(canvas, points, progress = 1) {
    if (!canvas || !points || points.length === 0) {
        return;
    }

    const { ctx, width, height, padding } = getHistoryCanvasMetrics(canvas);
    const values = points.map(point => point.balance);
    const range = getHistoryChartRange(values);
    const timeDomain = getHistoryChartTimeDomain(points);
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const bottom = height - padding.bottom;
    const getX = (point) => getHistoryChartX(point, timeDomain, padding, chartWidth);
    const getY = (value) => getHistoryChartY(value, range, padding, chartHeight);
    const clipWidth = padding.left + chartWidth * progress;

    ctx.clearRect(0, 0, width, height);
    drawHistoryGrid(ctx, width, height, padding, range, progress);

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, clipWidth, height);
    ctx.clip();

    const gradient = ctx.createLinearGradient(0, padding.top, 0, bottom);
    gradient.addColorStop(0, 'rgba(128, 128, 128, 0.18)');
    gradient.addColorStop(1, 'rgba(128, 128, 128, 0.02)');

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.moveTo(padding.left, bottom);
    points.forEach(point => {
        ctx.lineTo(getX(point), getY(point.balance));
    });
    ctx.lineTo(getX(points[points.length - 1]), bottom);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = '#808080';
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.beginPath();
    points.forEach((point, index) => {
        if (index === 0) {
            ctx.moveTo(getX(point), getY(point.balance));
        } else {
            ctx.lineTo(getX(point), getY(point.balance));
        }
    });
    ctx.stroke();

    ctx.restore();
}

function animateHistoryChart(points, duration = 760) {
    if (!historyCanvas) {
        return;
    }

    if (historyChartAnimationFrame) {
        cancelAnimationFrame(historyChartAnimationFrame);
        historyChartAnimationFrame = null;
    }

    const startedAt = performance.now();

    const frame = (now) => {
        const progress = Math.min((now - startedAt) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);

        drawHistoryChart(historyCanvas, points, eased);

        if (progress < 1) {
            historyChartAnimationFrame = requestAnimationFrame(frame);
        } else {
            drawHistoryChart(historyCanvas, points, 1);
            historyChartAnimationFrame = null;
        }
    };

    historyChartAnimationFrame = requestAnimationFrame(frame);
}

function renderHistoryChart(points, animate = true) {
    historyChartData = points || [];

    if (!historyChartData.length) {
        historySection.classList.remove('balance-history--loaded');
        return;
    }

    historySection.classList.add('balance-history--loaded');

    if (animate) {
        animateHistoryChart(historyChartData);
    } else {
        drawHistoryChart(historyCanvas, historyChartData, 1);
    }
}

function setupHistoryChartTooltip() {
    if (!historyCanvas || !historyChartTooltip) {
        return;
    }

    const padding = { top: 10, right: 0, bottom: 10, left: 0 };

    historyCanvas.addEventListener('mousemove', (event) => {
        const data = historyChartData;
        if (!data || data.length === 0) {
            return;
        }

        const rect = historyCanvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const chartWidth = rect.width - padding.left - padding.right;
        const chartHeight = rect.height - padding.top - padding.bottom;

        if (x < padding.left || x > rect.width - padding.right) {
            historyChartTooltip.classList.remove('balance-history-tooltip--visible');
            if (historyChartDot) {
                historyChartDot.classList.remove('balance-history-dot--visible');
            }
            return;
        }

        const timeDomain = getHistoryChartTimeDomain(data);
        let index = 0;
        let closestDistance = Infinity;

        data.forEach((item, itemIndex) => {
            const itemX = getHistoryChartX(item, timeDomain, padding, chartWidth);
            const distance = Math.abs(itemX - x);

            if (distance < closestDistance) {
                closestDistance = distance;
                index = itemIndex;
            }
        });

        const point = data[index];
        const values = data.map(item => item.balance);
        const range = getHistoryChartRange(values);
        const pointX = getHistoryChartX(point, timeDomain, padding, chartWidth);
        const pointY = getHistoryChartY(point.balance, range, padding, chartHeight);
        const valueEl = historyChartTooltip.querySelector('.balance-history-tooltip__value');
        const dateEl = historyChartTooltip.querySelector('.balance-history-tooltip__date');

        if (valueEl) {
            valueEl.textContent = formatBalance(point.balance);
        }

        if (dateEl) {
            dateEl.textContent = formatDate(point.date.toISOString());
        }

        const tooltipWidth = historyChartTooltip.offsetWidth || 136;
        const tooltipX = Math.max(tooltipWidth / 2, Math.min(rect.width - tooltipWidth / 2, pointX));
        historyChartTooltip.style.left = `${tooltipX}px`;
        historyChartTooltip.style.top = `${pointY - 10}px`;
        historyChartTooltip.classList.add('balance-history-tooltip--visible');

        if (historyChartDot) {
            historyChartDot.style.left = `${pointX}px`;
            historyChartDot.style.top = `${pointY}px`;
            historyChartDot.classList.add('balance-history-dot--visible');
        }
    });

    historyCanvas.addEventListener('mouseleave', () => {
        historyChartTooltip.classList.remove('balance-history-tooltip--visible');
        if (historyChartDot) {
            historyChartDot.classList.remove('balance-history-dot--visible');
        }
    });
}

// Выбор файла
function selectFile(file) {
    currentFile = file;
    updateCurrentDisplay();

    // Обновляем selected класс
    const items = dropdownList.querySelectorAll('.dropdown-item');
    items.forEach(item => {
        if (item.dataset.filename === file.filename) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });

    // Закрываем выпадающий список
    toggleDropdown();

    // Загружаем данные выбранного файла (анимация запустится в displayTotalStats)
    displayHistoryChart();
    loadAnalysisData(file.filename);
}

// Переключение выпадающего списка
function toggleDropdown() {
    const isActive = dataDropdown.classList.toggle('active');
    dataSelectorBtn.classList.toggle('active', isActive);
}

// Закрытие выпадающего списка при клике вне его
document.addEventListener('click', (e) => {
    if (!dataSelectorBtn.contains(e.target) && !dataDropdown.contains(e.target)) {
        dataDropdown.classList.remove('active');
        dataSelectorBtn.classList.remove('active');
    }
});

// Обработчик клика на кнопку
dataSelectorBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDropdown();
});

// Загрузка данных из выбранного JSON файла
async function loadAnalysisData(filename) {
    try {
        const response = await fetch(`data/${filename}`);
        if (!response.ok) {
            throw new Error('Failed to load analysis data');
        }

        currentData = await response.json();
        displayTotalStats();
    } catch (error) {
        console.error('Error loading analysis data:', error);
    }
}

// Отображение Total Stats (Categories и Tokens)
function displayTotalStats() {
    if (!currentData || !currentData.total_stats) {
        return;
    }

    displayTopSources();
    displayCategories();
    displayTokens();
    displayWalletGroups();

    let renderFinished = false;

    const finishRender = () => {
        if (renderFinished) {
            return;
        }

        renderFinished = true;

        if (isFirstLoad) {
            hideLoadingOverlay();
        } else {
            // При смене даты запускаем все анимации
            startAllAnimations();
        }
    };

    // Ждем ПОЛНОГО рендеринга для обоих случаев (первая загрузка и смена даты)
    waitForCompleteRender().then(finishRender);
    setTimeout(finishRender, 1500);
}

// Ожидание ПОЛНОГО завершения рендеринга и layout
function waitForCompleteRender() {
    return new Promise((resolve) => {
        // Сначала проверяем готовность всех элементов
        waitForElementsReady().then(() => {
            // Показываем все квадратики СРАЗУ (без анимации) для производительности
            showAllSquaresInstantly();

            // Элементы готовы, но браузер может все еще делать layout
            // Используем requestAnimationFrame цепочку для ожидания paint
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    // Теперь ждем когда браузер будет idle (свободен)
                    waitForBrowserIdle().then(() => {
                        resolve();
                    });
                });
            });
        });
    });
}

// Показать все квадратики мгновенно (без анимации) для первой загрузки
function showAllSquaresInstantly() {
    // Сбрасываем старые классы если они есть
    const allSquares = document.querySelectorAll('.progress-square');
    allSquares.forEach(square => {
        square.classList.remove('visible', 'animate');
        square.style.animationDelay = '';
    });

    // Показываем квадратики в основной статистике МГНОВЕННО
    const visibleSquares = document.querySelectorAll('.progress-bar .progress-square[data-visible="true"]');
    visibleSquares.forEach(square => {
        square.classList.add('visible');
    });
}

// Запуск всех анимаций (используется при смене даты)
function startAllAnimations() {
    // Сбрасываем все квадратики
    const allSquares = document.querySelectorAll('.progress-square');
    allSquares.forEach(square => {
        square.classList.remove('visible', 'animate');
        square.style.animationDelay = '';
    });

    // Запускаем анимацию квадратиков через CSS (быстрее чем JS)
    requestAnimationFrame(() => {
        animateProgressBarsCSS();
        // Балансы и scramble запускаются параллельно
        animateBalances();
        scrambleInstances.forEach(instance => instance.trigger());
    });
}

// Ожидание готовности всех элементов DOM
function waitForElementsReady() {
    return new Promise((resolve) => {
        const checkReady = () => {
            // Проверяем наличие ключевых элементов (кошельки могут отсутствовать - это нормально)
            const categoriesExist = document.querySelectorAll('.category-item').length > 0;
            const tokensExist = document.querySelectorAll('.token-item').length > 0;
            const progressBarsExist = document.querySelectorAll('.progress-square').length > 0;

            // Если основные элементы существуют - готово (кошельки опциональны)
            if (categoriesExist && tokensExist && progressBarsExist) {
                resolve();
            } else {
                // Если нет - проверяем снова через 10ms
                setTimeout(checkReady, 10);
            }
        };

        checkReady();
    });
}

// Ожидание когда браузер завершит layout и будет свободен
function waitForBrowserIdle() {
    return new Promise((resolve) => {
        let isResolved = false;

        const finish = () => {
            if (isResolved) {
                return;
            }

            isResolved = true;
            requestAnimationFrame(() => {
                resolve();
            });
        };

        const timeoutId = setTimeout(finish, 700);

        // Используем requestIdleCallback если доступен (лучший вариант)
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                clearTimeout(timeoutId);
                finish();
            }, { timeout: 500 }); // Максимум 500ms ожидания
        } else {
            // Fallback для старых браузеров - просто задержка
            setTimeout(() => {
                clearTimeout(timeoutId);
                finish();
            }, 100);
        }
    });
}

// Получение топа самых крупных источников
function getTopSources(limit = 5) {
    if (!currentData || !currentData.categories) {
        return [];
    }

    const exchangeCategories = ['OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];
    const sources = [];

    for (const categoryName in currentData.categories) {
        const category = currentData.categories[categoryName];
        const items = category.items || [];
        const sourceType = exchangeCategories.includes(categoryName) ? 'Exchange' : 'Wallet';

        items.forEach(item => {
            const balance = Number((item.balances || {}).total || 0);

            if (balance <= 0) {
                return;
            }

            const name = item.name || categoryName;
            const group = item.group || '';
            const identifier = item.api_key_last4
                ? `****${item.api_key_last4}`
                : (item.address || '');

            sources.push({
                categoryName,
                sourceType,
                name,
                group,
                identifier,
                balance,
                label: name
            });
        });
    }

    return sources
        .sort((a, b) => b.balance - a.balance)
        .slice(0, limit);
}

// Отображение топа самых крупных источников
function displayTopSources() {
    if (!topSourcesSection || !topSourcesList) {
        return;
    }

    const sources = getTopSources(5);
    const totalBalance = Number((currentData.metadata || {}).total_balance || 0);

    topSourcesList.innerHTML = '';

    if (sources.length === 0 || totalBalance <= 0) {
        topSourcesSection.hidden = true;
        return;
    }

    topSourcesSection.hidden = false;

    sources.forEach(source => {
        const sourcePercent = (source.balance / totalBalance) * 100;
        const sourceItem = document.createElement('div');
        sourceItem.className = 'top-source-item';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'top-source-name';
        nameSpan.textContent = source.label;
        nameSpan.title = [
            `${source.sourceType}: ${source.categoryName}`,
            source.group ? `Group: ${source.group}` : null,
            source.identifier ? `ID: ${source.identifier}` : null
        ].filter(Boolean).join(' | ');

        const progressBar = createProgressBar(sourcePercent, false);

        const balanceSpan = document.createElement('span');
        balanceSpan.className = 'top-source-balance';
        balanceSpan.textContent = '$0';
        balanceSpan.dataset.targetValue = source.balance;

        sourceItem.appendChild(nameSpan);
        sourceItem.appendChild(progressBar);
        sourceItem.appendChild(balanceSpan);
        topSourcesList.appendChild(sourceItem);
    });
}

// Отображение Categories
function displayCategories() {
    const categoriesList = document.getElementById('categoriesList');
    const categories = currentData.total_stats.categories;
    const totalBalance = currentData.metadata.total_balance;

    // Порядок категорий
    const categoryOrder = ['EVM', 'SOL', 'BTC', 'APT', 'TRX', 'OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];

    // Названия подкатегорий
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
        trx: 'TRX',
        usdt: 'USDT',
        other_tokens: 'Other Tokens',
        staked_apt: 'Staked APT'
    };

    categoriesList.innerHTML = '';

    categoryOrder.forEach(categoryName => {
        if (!categories[categoryName]) return;

        const category = categories[categoryName];
        const categoryPercent = (category.total / totalBalance) * 100;

        // Создаем элемент категории
        const categoryItem = document.createElement('div');
        categoryItem.className = 'category-item';

        // Основная строка категории
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

        // Подкатегории (если есть)
        const subcategories = getSubcategories(category, categoryName);
        if (subcategories.length > 0) {
            // Сортируем подкатегории по убыванию значения
            subcategories.sort((a, b) => b.value - a.value);

            subcategories.forEach(sub => {
                // Процент от родительской категории
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

// Получение подкатегорий для категории
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
            trx: 'TRX',
            usdt: 'USDT',
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

// Отображение Tokens
function displayTokens() {
    const tokensList = document.getElementById('tokensList');
    const tokens = currentData.total_stats.tokens;
    const totalBalance = currentData.metadata.total_balance;

    tokensList.innerHTML = '';

    // Tokens уже отсортированы по убыванию в JSON
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

// Отображение Wallet Groups (все категории)
function displayWalletGroups() {
    const walletGroupsSection = document.getElementById('walletGroupsSection');

    if (!currentData || !currentData.categories) {
        walletGroupsSection.innerHTML = '';
        return;
    }

    walletGroupsSection.innerHTML = '';

    // Определяем порядок категорий
    const categoryOrder = ['EVM', 'SOL', 'BTC', 'APT', 'TRX', 'OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];

    // Определяем какие категории являются биржами
    const exchangeCategories = ['OKX', 'BINANCE', 'BYBIT', 'BACKPACK', 'KUCOIN', 'MEXC', 'GATE'];

    // Обрабатываем каждую категорию
    categoryOrder.forEach(categoryName => {
        if (!currentData.categories[categoryName] || !currentData.categories[categoryName].items) {
            return; // Пропускаем если категория отсутствует
        }

        const items = currentData.categories[categoryName].items;
        const isExchange = exchangeCategories.includes(categoryName);

        // Группируем по group
        const groupedItems = {};
        items.forEach(item => {
            const groupName = item.group || 'Unknown';
            if (!groupedItems[groupName]) {
                groupedItems[groupName] = [];
            }
            groupedItems[groupName].push(item);
        });

        // Создаем секции для каждой группы
        for (const groupName in groupedItems) {
            const groupItems = groupedItems[groupName];

            const groupDiv = document.createElement('div');
            groupDiv.className = 'wallet-group';

            // Заголовок группы
            const groupTitle = document.createElement('h2');
            groupTitle.className = 'wallet-group-title';
            groupTitle.textContent = `${categoryName} - ${groupName}`;
            groupDiv.appendChild(groupTitle);

            // Заголовок таблицы
            const tableHeader = document.createElement('div');
            tableHeader.className = 'wallet-table-header';

            if (isExchange) {
                // Для бирж: Name, API Key, Balance
                tableHeader.innerHTML = `
                    <span class="wallet-header-name">Name</span>
                    <span class="wallet-header-address">API Key</span>
                    <span class="wallet-header-balance">Balance</span>
                `;
            } else {
                // Для кошельков: Name, Address, Balance
                tableHeader.innerHTML = `
                    <span class="wallet-header-name">Name</span>
                    <span class="wallet-header-address">Address</span>
                    <span class="wallet-header-balance">Balance</span>
                `;
            }
            groupDiv.appendChild(tableHeader);

            // Создаем строки для каждого элемента
            groupItems.forEach(item => {
                const itemRow = createWalletRow(item, categoryName, isExchange);
                groupDiv.appendChild(itemRow);
            });

            walletGroupsSection.appendChild(groupDiv);
        }
    });
}

// Создание строки кошелька
function createWalletRow(wallet, categoryName, isExchange = false) {
    const walletRow = document.createElement('div');
    walletRow.className = 'wallet-row';

    // Обрезаем имя если длиннее 16 символов
    let displayName = wallet.name;
    if (displayName.length > 16) {
        displayName = displayName.substring(0, 13) + '...';
    }

    // Основная строка
    const walletRowMain = document.createElement('div');
    walletRowMain.className = 'wallet-row-main';

    // Создаем элементы отдельно чтобы добавить data-target-value
    const nameSpan = document.createElement('span');
    nameSpan.className = 'wallet-name';
    nameSpan.textContent = displayName;

    const addressSpan = document.createElement('span');
    addressSpan.className = 'wallet-address';

    if (isExchange) {
        // Для бирж показываем API Key (последние 4 символа)
        addressSpan.textContent = wallet.api_key_last4 ? `****${wallet.api_key_last4}` : 'N/A';
    } else {
        // Для кошельков показываем адрес
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

    // Детали кошелька (скрыты по умолчанию)
    const walletDetails = createWalletDetails(wallet, categoryName);
    walletRow.appendChild(walletDetails);

    // Обработчик клика для раскрытия/скрытия
    walletRowMain.addEventListener('click', () => {
        const wasExpanded = walletRow.classList.contains('expanded');
        walletRow.classList.toggle('expanded');

        // Если только что раскрыли - запускаем анимацию
        if (!wasExpanded) {
            // Небольшая задержка чтобы DOM успел отрендериться
            setTimeout(() => {
                animateWalletDetails(walletRow);
            }, 10);
        }
    });

    return walletRow;
}

// Создание детальной информации кошелька
function createWalletDetails(wallet, categoryName) {
    const walletDetails = document.createElement('div');
    walletDetails.className = 'wallet-details';

    const balances = wallet.balances;
    const tokens = wallet.tokens || {};
    const totalBalance = balances.total;

    // Вспомогательная функция для добавления токенов
    const addTokens = (parentLabel = null) => {
        if (Object.keys(tokens).length === 0) return;

        // Отделяем "Other" от остальных токенов
        const otherEntry = Object.entries(tokens).find(([name]) => name === 'Other');
        const regularTokens = Object.entries(tokens).filter(([name]) => name !== 'Other');

        // Сортируем обычные токены по убыванию
        const sortedTokens = regularTokens.sort((a, b) => b[1] - a[1]);

        // Добавляем обычные токены
        sortedTokens.forEach(([tokenName, tokenValue]) => {
            const prefix = parentLabel ? '└─ ' : '';
            const tokenItem = createDetailItem(`${prefix}${tokenName}`, tokenValue, totalBalance, true);
            walletDetails.appendChild(tokenItem);
        });

        // Добавляем "Other" в конец, если он есть
        if (otherEntry) {
            const [tokenName, tokenValue] = otherEntry;
            const prefix = parentLabel ? '└─ ' : '';
            const tokenItem = createDetailItem(`${prefix}${tokenName}`, tokenValue, totalBalance, true);
            walletDetails.appendChild(tokenItem);
        }
    };

    // === EVM ===
    if (categoryName === 'EVM') {
        // Chains
        if (balances.chains > 0) {
            const chainsItem = createDetailItem('Chains', balances.chains, totalBalance, false);
            walletDetails.appendChild(chainsItem);
            addTokens('Chains'); // Токены под Chains
        }

        // DeFi & Other
        if (balances.defi_other > 0) {
            const defiItem = createDetailItem('DeFi & Other', balances.defi_other, totalBalance, false);
            walletDetails.appendChild(defiItem);
        }

        // Polymarket Positions
        if (balances.polymarket_positions > 0) {
            const polyPosItem = createDetailItem('Polymarket Positions', balances.polymarket_positions, totalBalance, false);
            walletDetails.appendChild(polyPosItem);
        }

        // Polymarket Total
        if (balances.polymarket_total > 0) {
            const polyTotalItem = createDetailItem('Polymarket Total', balances.polymarket_total, totalBalance, false);
            walletDetails.appendChild(polyTotalItem);
        }

        // Hyperliquid Total
        if (balances.hyperliquid > 0) {
            const hyperItem = createDetailItem('Hyperliquid Total', balances.hyperliquid, totalBalance, false);
            walletDetails.appendChild(hyperItem);
        }

        // Lighter
        if (balances.lighter > 0) {
            const lighterItem = createDetailItem('Lighter', balances.lighter, totalBalance, false);
            walletDetails.appendChild(lighterItem);
        }
    }

    // === SOL ===
    else if (categoryName === 'SOL') {
        // Tokens (основная категория)
        if (balances.tokens > 0) {
            const tokensItem = createDetailItem('Tokens', balances.tokens, totalBalance, false);
            walletDetails.appendChild(tokensItem);
            addTokens('Tokens'); // Токены под Tokens
        }

        // DeFi
        if (balances.defi > 0) {
            const defiItem = createDetailItem('DeFi', balances.defi, totalBalance, false);
            walletDetails.appendChild(defiItem);
        }
    }

    // === BTC ===
    else if (categoryName === 'BTC') {
        // BTC
        if (balances.btc > 0) {
            const btcItem = createDetailItem('BTC', balances.btc, totalBalance, false);
            walletDetails.appendChild(btcItem);
        }

        // Runes
        if (balances.runes > 0) {
            const runesItem = createDetailItem('Runes', balances.runes, totalBalance, false);
            walletDetails.appendChild(runesItem);
        }

        // Inscriptions
        if (balances.inscriptions > 0) {
            const inscrItem = createDetailItem('Inscriptions', balances.inscriptions, totalBalance, false);
            walletDetails.appendChild(inscrItem);
        }
    }

    // === APT ===
    else if (categoryName === 'APT') {
        // APT (основной токен)
        if (balances.apt > 0) {
            const aptItem = createDetailItem('APT', balances.apt, totalBalance, false);
            walletDetails.appendChild(aptItem);
        }

        // Staked APT
        if (balances.staked_apt > 0) {
            const stakedItem = createDetailItem('Staked APT', balances.staked_apt, totalBalance, false);
            walletDetails.appendChild(stakedItem);
        }

        // Токены (все кроме "APT" и "Other")
        if (Object.keys(tokens).length > 0) {
            const otherEntry = Object.entries(tokens).find(([name]) => name === 'Other');
            const regularTokens = Object.entries(tokens).filter(([name]) => name !== 'APT' && name !== 'Other');

            // Сортируем обычные токены по убыванию
            const sortedTokens = regularTokens.sort((a, b) => b[1] - a[1]);

            // Добавляем обычные токены
            sortedTokens.forEach(([tokenName, tokenValue]) => {
                const tokenItem = createDetailItem(tokenName, tokenValue, totalBalance, false);
                walletDetails.appendChild(tokenItem);
            });

            // Добавляем "Other" в конец, если он есть
            if (otherEntry) {
                const [tokenName, tokenValue] = otherEntry;
                const tokenItem = createDetailItem(tokenName, tokenValue, totalBalance, false);
                walletDetails.appendChild(tokenItem);
            }
        }
    }

    // === TRX ===
    else if (categoryName === 'TRX') {
        if (balances.trx > 0) {
            const trxItem = createDetailItem('TRX', balances.trx, totalBalance, false);
            walletDetails.appendChild(trxItem);
        }

        if (balances.usdt > 0) {
            const usdtItem = createDetailItem('USDT', balances.usdt, totalBalance, false);
            walletDetails.appendChild(usdtItem);
        }

        if (balances.other_tokens > 0) {
            const otherTokensItem = createDetailItem('Other Tokens', balances.other_tokens, totalBalance, false);
            walletDetails.appendChild(otherTokensItem);

            const otherEntry = Object.entries(tokens).find(([name]) => name === 'Other');
            const regularTokens = Object.entries(tokens).filter(([name]) => !['TRX', 'USDT', 'Other'].includes(name));
            const sortedTokens = regularTokens.sort((a, b) => b[1] - a[1]);

            sortedTokens.forEach(([tokenName, tokenValue]) => {
                const tokenItem = createDetailItem(`└─ ${tokenName}`, tokenValue, totalBalance, true);
                walletDetails.appendChild(tokenItem);
            });

            if (otherEntry) {
                const [tokenName, tokenValue] = otherEntry;
                const tokenItem = createDetailItem(`└─ ${tokenName}`, tokenValue, totalBalance, true);
                walletDetails.appendChild(tokenItem);
            }
        }
    }

    // === Биржи ===
    else {
        // Для бирж только показываем токены (если есть)
        addTokens(null);
    }

    return walletDetails;
}

// Создание элемента детали (категория или токен)
function createDetailItem(name, value, totalBalance, isToken) {
    const detailItem = document.createElement('div');
    detailItem.className = 'wallet-detail-item';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'wallet-detail-name';
    if (isToken) {
        nameSpan.classList.add('token');
    }
    nameSpan.textContent = name;

    // Прогресс бар с квадратиками
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

// Создание прогресс бара для деталей кошелька
function createWalletDetailBar(percent, isToken) {
    const TOTAL_SQUARES = 130; // 137 квадратов для деталей кошелька
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

// Создание полоски прогресса с квадратиками
function createProgressBar(percent, isSubcategory) {
    const TOTAL_SQUARES = 144; // Всего квадратиков для 100%

    // Вычисляем сколько квадратиков показать
    let squaresToShow = Math.round((percent / 100) * TOTAL_SQUARES);

    // Минимум 1 квадратик ВСЕГДА (даже если баланс = 0)
    if (squaresToShow === 0) {
        squaresToShow = 1;
    }

    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';

    // Создаем ТОЛЬКО нужные квадратики (оптимизация)
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

// Анимация квадратиков через CSS (оптимизированная версия)
function animateProgressBarsCSS() {
    const progressBars = document.querySelectorAll('.progress-bar');

    progressBars.forEach(bar => {
        const squares = bar.querySelectorAll('.progress-square[data-visible="true"]');

        squares.forEach((square, index) => {
            // Используем CSS animation-delay вместо setTimeout (производительнее)
            square.style.animationDelay = `${index * 5}ms`;
            // Добавляем ТОЛЬКО класс animate - animation с fill-mode: both сама установит visibility
            square.classList.add('animate');
        });
    });
}

// Старая функция animateProgressBars (для обратной совместимости с раскрытием кошельков)
function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar, .wallet-detail-bar');

    progressBars.forEach(bar => {
        const squares = bar.querySelectorAll('.progress-square[data-visible="true"]');

        squares.forEach((square, index) => {
            // Задержка для появления один за одним внутри каждой полоски
            setTimeout(() => {
                square.classList.add('visible');
            }, index * 5); // 5ms задержка между квадратиками
        });
    });

    // Запуск анимации всех балансов одновременно с квадратиками
    animateBalances();
}

// Анимация всех балансов на странице
function animateBalances() {
    // Максимальная длительность = 144 квадрата × 5ms = 720ms
    const duration = 720;

    // Анимация баланса в кнопке выбора даты
    if (currentBalance.dataset.targetValue) {
        const targetValue = parseFloat(currentBalance.dataset.targetValue);
        currentBalance.textContent = '$0';
        animateBalance(currentBalance, targetValue, duration);
    }

    // Анимация всех балансов категорий
    document.querySelectorAll('.category-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    // Анимация всех балансов подкатегорий
    document.querySelectorAll('.subcategory-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    // Анимация всех балансов токенов
    document.querySelectorAll('.token-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    // Анимация балансов топ-источников
    document.querySelectorAll('.top-source-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    // Анимация всех балансов в деталях кошельков
    document.querySelectorAll('.wallet-detail-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });

    // Анимация балансов в основных строках кошельков
    document.querySelectorAll('.wallet-total-balance').forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });
}

// Анимация деталей раскрытого кошелька
function animateWalletDetails(walletRow) {
    const duration = 720;

    // Анимация квадратиков в деталях кошелька
    const detailBars = walletRow.querySelectorAll('.wallet-detail-bar');
    detailBars.forEach(bar => {
        const squares = bar.querySelectorAll('.progress-square[data-visible="true"]');
        squares.forEach((square, index) => {
            // Сначала скрываем все квадратики
            square.classList.remove('visible');
            // Затем показываем с задержкой
            setTimeout(() => {
                square.classList.add('visible');
            }, index * 5);
        });
    });

    // Анимация балансов в деталях
    const detailBalances = walletRow.querySelectorAll('.wallet-detail-balance');
    detailBalances.forEach(element => {
        if (element.dataset.targetValue) {
            const targetValue = parseFloat(element.dataset.targetValue);
            element.textContent = '$0';
            animateBalance(element, targetValue, duration);
        }
    });
}

// Scramble Text Animation
class ScrambleText {
    constructor(element, options = {}) {
        this.element = element;
        // Сохраняем оригинальный HTML (с <br> если есть)
        this.originalHTML = element.innerHTML;
        this.originalText = element.dataset.text || element.textContent.replace(/\n/g, '');

        // Определяем тип символов для мельтешения
        const isNumericVersion = /^\d+\.\d+\.\d+$/.test(this.originalText.trim());
        if (isNumericVersion) {
            this.chars = '0123456789';
            // Для версии (цифр) - медленнее
            this.frameRate = options.frameRate || 30;
            this.iterations = options.iterations || 4;
            this.scrambleCount = options.scrambleCount || 2;
        } else {
            this.chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
            // Для текста - обычная скорость
            this.frameRate = options.frameRate || 16;
            this.iterations = options.iterations || 2;
            this.scrambleCount = options.scrambleCount || 20;
        }

        this.frameRequest = null;
        this.frame = 0;
        this.isAnimating = false;
        this.lastAnimationTime = 0;
        this.cooldown = 5000; // 5 секунд cooldown

        this.element.addEventListener('mouseenter', () => this.scrambleWithCooldown());
    }

    scrambleWithCooldown() {
        const now = Date.now();
        if (now - this.lastAnimationTime < this.cooldown) {
            return; // Cooldown активен, игнорируем
        }
        this.scramble();
    }

    trigger() {
        // Принудительный запуск без проверки cooldown (для автозапуска)
        this.scramble();
    }

    getRandomChar(originalChar) {
        // Определяем регистр оригинального символа
        const isUpperCase = originalChar === originalChar.toUpperCase();

        // Фильтруем символы по регистру
        let availableChars;
        if (isUpperCase) {
            availableChars = this.chars.split('').filter(c => c === c.toUpperCase()).join('');
        } else {
            availableChars = this.chars.split('').filter(c => c === c.toLowerCase() && c !== c.toUpperCase()).join('');
        }

        // Если нет подходящих символов (например, для цифр), используем все
        if (availableChars.length === 0) {
            availableChars = this.chars;
        }

        return availableChars[Math.floor(Math.random() * availableChars.length)];
    }

    scramble() {
        if (this.isAnimating) return;

        this.isAnimating = true;
        this.lastAnimationTime = Date.now(); // Обновляем время последней анимации
        this.frame = 0;

        const animate = () => {
            let output = '';
            let revealedCount = 0; // Количество раскрытых символов
            let allComplete = true;

            // Вычисляем сколько символов должно быть раскрыто
            const shouldReveal = Math.floor(this.frame / this.iterations);

            for (let i = 0; i < this.originalText.length; i++) {
                const char = this.originalText[i];

                // Вставляем <br> после "Balance Checker" (15 символов)
                if (this.originalHTML.includes('<br>') && i === 15) {
                    output += '<br>';
                }

                // Пробелы и точки всегда показываем (не считаем как символы)
                if (char === ' ' || char === '.') {
                    output += char;
                    continue;
                }

                if (revealedCount < shouldReveal) {
                    // Символ раскрыт
                    output += char;
                    revealedCount++;
                } else if (revealedCount >= shouldReveal && revealedCount < shouldReveal + this.scrambleCount) {
                    // Символ мельтешит (следующие N символов после раскрытых)
                    const randomChar = this.getRandomChar(char);
                    output += `<span class="scramble-char">${randomChar}</span>`;
                    revealedCount++;
                    allComplete = false;
                } else {
                    // Остальное не показываем
                    allComplete = false;
                    break;
                }
            }

            this.element.innerHTML = output;

            if (!allComplete) {
                this.frame++;
                this.frameRequest = setTimeout(animate, this.frameRate);
            } else {
                // Восстанавливаем оригинальный HTML с <br>
                this.element.innerHTML = this.originalHTML;
                this.isAnimating = false;
            }
        };

        animate();
    }
}

// Скрытие loading overlay и запуск анимаций
function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');

    // Скрываем overlay с fade-out анимацией
    overlay.classList.add('hidden');

    // После начала fade-out запускаем анимации (через 100ms)
    setTimeout(() => {
        startAllAnimations();
        isFirstLoad = false; // Больше не первая загрузка
    }, 100);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('Balance Checker Combine загружен');

    // Инициализация scramble эффекта (до loadFilesList)
    document.querySelectorAll('.scramble-text').forEach(element => {
        const instance = new ScrambleText(element);
        scrambleInstances.push(instance);
    });

    setupHistoryChartTooltip();
    updateHistoryRangeButtons();
    initHistoryRangeSlider();

    // Загрузка данных (overlay скроется автоматически после рендеринга)
    loadFilesList();
});

historyRangeButtons.forEach(button => {
    button.addEventListener('click', () => {
        activeHistoryRange = button.dataset.range || '30d';
        updateHistoryRangeButtons();
        moveHistoryRangeSlider(button);
        displayHistoryChart(true);
    });
});

let historyResizeTimer = null;
window.addEventListener('resize', () => {
    clearTimeout(historyResizeTimer);
    historyResizeTimer = setTimeout(() => {
        initHistoryRangeSlider();
        displayHistoryChart(false);
    }, 100);
});
