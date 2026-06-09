#!/usr/bin/env node
/**
 * Генератор подписей с ВНЕШНИМ nonce (генерируется в Python)
 * Решение проблемы с одинаковым nonce в Node.js
 */

const nodeCrypto = require('crypto');

// Полифиллы для браузерного окружения
try {
    Object.defineProperty(globalThis, 'crypto', {
        value: {
            getRandomValues(buffer) {
                return nodeCrypto.randomFillSync(buffer);
            },
            subtle: nodeCrypto.webcrypto?.subtle || {}
        },
        configurable: true,
        writable: false
    });
} catch (e) {
    if (!globalThis.crypto) {
        globalThis.crypto = {
            getRandomValues(buffer) { return nodeCrypto.randomFillSync(buffer); },
            subtle: {}
        };
    }
}

globalThis.self = globalThis;
globalThis.window = globalThis;
globalThis.browser = undefined;
globalThis.chrome = undefined;
globalThis.atob = (str) => Buffer.from(str, 'base64').toString('binary');
globalThis.btoa = (str) => Buffer.from(str, 'binary').toString('base64');

const sign = require('@rabby-wallet/rabby-sign/umd/sign-wasm-rabby');

async function main() {
    const args = process.argv.slice(2);

    if (args.length < 4) {
        console.error('Usage: node generate_signature_with_nonce.js <method> <url> <params_json> <custom_nonce>');
        process.exit(1);
    }

    const method = args[0];
    const url = args[1];
    const paramsJson = args[2];
    const customNonce = args[3]; // ВАЖНО: nonce передается извне!

    try {
        // Инициализация WASM
        await sign.lW('');

        // Парсим параметры
        const params = JSON.parse(paramsJson);

        // Генерируем подпись с КАСТОМНЫМ nonce и timestamp
        const timestamp = Math.floor(Date.now() / 1000);

        // Используем внутреннюю функцию cattleSF для генерации подписи с нашим nonce
        const signature = sign.cattleSF(method, url, params, customNonce, timestamp);

        // Выводим результат
        console.log(JSON.stringify({
            'x-api-ts': timestamp,
            'x-api-nonce': customNonce,
            'x-api-ver': 'v2',
            'x-api-sign': signature
        }));

    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

main();
