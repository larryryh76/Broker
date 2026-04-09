import asyncio
import os
import random
from playwright.async_api import Page, BrowserContext
from typing import Optional

class TitanInteractionSuite:
    @staticmethod
    async def apply_ui_sensitivity(page: Page):
        """V5.21 UI Sensitivity Suite: Modals, Theme, Z-Index, Asset Retry, Preconnect."""
        print("DEBUG: Injecting V5.21 UI Sensitivity Suite...")

        # V5.21: Preconnect/DNS-Prefetch Tags
        await page.add_init_script("""
            (function() {
                const head = document.head || document.getElementsByTagName('head')[0];
                const domains = ['https://www.football.com', 'https://s.football.com/games/'];
                domains.forEach(url => {
                    const pc = document.createElement('link'); pc.rel = 'preconnect'; pc.href = url; head.appendChild(pc);
                    const dp = document.createElement('link'); dp.rel = 'dns-prefetch'; dp.href = url; head.appendChild(dp);
                });
            })();
        """)

        await page.add_init_script("""
            (function() {
                // 1. Asset Retry Hook
                window.assetRetries = window.assetRetries || {};
                const originalCreateElement = document.createElement;
                document.createElement = function(tagName) {
                    const element = originalCreateElement.call(document, tagName);
                    if (tagName === 'script' || tagName === 'link') {
                        element.onerror = function() {
                            const src = element.src || element.href;
                            if (!src) return;
                            window.assetRetries[src] = (window.assetRetries[src] || 0) + 1;
                            if (window.assetRetries[src] <= 2) {
                                console.log(`Retrying asset: ${src} (Attempt ${window.assetRetries[src]})`);
                                const newEl = document.createElement(tagName);
                                if (tagName === 'script') newEl.src = src; else newEl.href = src;
                                document.head.appendChild(newEl);
                            } else {
                                console.error(`Fatal Error: Asset load failed after 2 retries: ${src}`);
                            }
                        };
                    }
                    return element;
                };

                // 2. Global Modal & Auth Listener
                const originalFetch = window.fetch;
                window.fetch = async (...args) => {
                    const response = await originalFetch(...args);
                    if (response.status === 401) {
                        triggerLoginModal();
                    }
                    return response;
                };

                function triggerLoginModal() {
                    if (document.getElementById('omni-auth-modal')) return;
                    const modal = document.createElement('div');
                    modal.id = 'omni-auth-modal';
                    modal.innerHTML = `
                        <div class="modal-backdrop" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1052;"></div>
                        <div class="modal-content" style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;z-index:1055;border-radius:8px;text-align:center;width:80%;">
                            <h3>Error! Please login to start game.</h3>
                            <button id="auth-primary" style="background:#007bff;color:white;padding:10px 20px;border:none;border-radius:4px;margin:5px;">Login</button>
                            <button id="auth-secondary" style="background:#6c757d;color:white;padding:10px 20px;border:none;border-radius:4px;margin:5px;">Exit</button>
                        </div>
                    `;
                    document.body.appendChild(modal);
                    document.getElementById('auth-primary').onclick = () => window.location.href = '/ng/m/login';
                    document.getElementById('auth-secondary').onclick = () => {
                        modal.remove();
                        window.history.back() || (window.location.href = '/ng/m/home');
                    };
                }

                // 3. Theme & Z-Index Management
                let modalStack = 0;
                const updateTheme = () => {
                    const theme = document.documentElement.getAttribute('data-theme') || 'light';
                    const brand = window.BRAND_NAME || 'football';
                    const loaders = document.querySelectorAll('.app-init-loader-wrap, .m-loader, .loading-wrap');
                    const spinners = document.querySelectorAll('.spinner-icon');

                    loaders.forEach(loader => {
                        if (theme === 'light') {
                            loader.style.setProperty('background-color', '#f4f4f4', 'important');
                        } else {
                            loader.style.setProperty('background-color', (brand === 'Encore') ? '#100e26' : '#000000', 'important');
                        }
                    });

                    if (theme === 'light') {
                        spinners.forEach(s => s.style.setProperty('background-color', '#e0e1e2', 'important'));
                    }
                };

                const observer = new MutationObserver(() => {
                    updateTheme();
                    const backdrops = document.querySelectorAll('.modal-backdrop:not([data-managed])');
                    backdrops.forEach(b => {
                        b.style.zIndex = (1052 + (modalStack * 10)).toString();
                        b.setAttribute('data-managed', 'true');
                    });
                    const contents = document.querySelectorAll('.modal-content:not([data-managed])');
                    contents.forEach(c => {
                        c.style.zIndex = (1055 + (modalStack * 10)).toString();
                        c.setAttribute('data-managed', 'true');
                        modalStack++;
                    });
                });
                observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });
            })();
        """)

    @staticmethod
    async def stabilize_environment(page: Page):
        """V5.34 DOM-NUKE & Stabilization: Physically delete traps."""
        print("DEBUG: Executing DOM-NUKE Stabilization...")
        try:
            # V5.34: Aggressively delete modal traps and overlays
            await page.evaluate("""
                const nukes = ['.m-modal', '.overlay', '[class*="backdrop"]', '.dialog-wrap', '.sg-confirm-cancel-modal-v2', '.app-init-loader-wrap', '.m-loader', '.loading-wrap', '.m-loading-mask', '.app-loading', '#app-loading'];
                nukes.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        console.log('DOM-NUKE: Removing ' + sel);
                        el.remove();
                    });
                });
            """)
        except: pass
        try: await page.mouse.click(0, 0)
        except: pass

    @staticmethod
    async def hide_init_loader(page: Page):
        """V5.21: Immediately hide the loader when state is 'Ready'."""
        try:
            await page.evaluate("""
                const selectors = ['.app-init-loader-wrap', '.m-loader', '.loading-wrap', '.m-loading-mask'];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        el.style.display = 'none';
                        el.style.opacity = '0';
                        el.style.visibility = 'hidden';
                    });
                });
            """)
        except: pass

    @staticmethod
    async def human_jiggle(page: Page):
        try:
            await page.mouse.wheel(0, 200)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await page.mouse.wheel(0, -200)
            await asyncio.sleep(0.5)
        except: pass
