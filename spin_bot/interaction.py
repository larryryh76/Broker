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
                if (!head) return;
                const domains = ['https://www.football.com', 'https://s.football.com/games/'];
                domains.forEach(url => {
                    const pc = document.createElement('link'); pc.rel = 'preconnect'; pc.href = url; head.appendChild(pc);
                    const dp = document.createElement('link'); dp.rel = 'dns-prefetch'; dp.href = url; head.appendChild(dp);
                });
            })();
        """)

        await page.add_init_script("""
            (function() {
                console.log("[V5.21] Init Script Running");

                const onReady = (cb) => {
                    if (document.body) cb();
                    else window.addEventListener('DOMContentLoaded', cb);
                };

                // 1. Asset Retry Hook
                window.assetRetries = window.assetRetries || {};
                const originalCreateElement = document.createElement;
                document.createElement = function(tagName) {
                    const element = originalCreateElement.call(document, tagName);
                    const tag = tagName.toLowerCase();
                    if (tag === 'script' || tag === 'link') {
                        element.onerror = function() {
                            const src = element.src || element.href;
                            if (!src) return;
                            window.assetRetries[src] = (window.assetRetries[src] || 0) + 1;
                            if (window.assetRetries[src] <= 2) {
                                console.log(`[V5.21] Retrying asset: ${src} (Attempt ${window.assetRetries[src]})`);
                                const newEl = document.createElement(tagName);
                                if (tag === 'script') {
                                    newEl.src = src;
                                    newEl.async = true;
                                } else {
                                    newEl.href = src;
                                    newEl.rel = 'stylesheet';
                                }
                                onReady(() => document.head.appendChild(newEl));
                            } else {
                                console.error(`[V5.21] Fatal Error: Asset load failed after 2 retries: ${src}`);
                                if (!document.getElementById('titan-fatal-error')) {
                                    const errDiv = document.createElement('div');
                                    errDiv.id = 'titan-fatal-error';
                                    errDiv.style = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);color:white;z-index:9999;display:flex;align-items:center;justify-content:center;text-align:center;padding:20px;font-family:sans-serif;";
                                    errDiv.innerHTML = "<div><h1>Fatal Error</h1><p>Failed to load essential assets. Please check your connection and refresh.</p><button onclick='location.reload()' style='padding:10px 20px;margin-top:20px;'>Retry Manually</button></div>";
                                    document.body.appendChild(errDiv);
                                }
                            }
                        };
                    }
                    return element;
                };

                // 2. Global Modal & Auth Listener
                const originalFetch = window.fetch;
                window.fetch = async (...args) => {
                    try {
                        const response = await originalFetch(...args);
                        if (response && response.status === 401) {
                            window.dispatchEvent(new CustomEvent('titan-login-required'));
                        }
                        return response;
                    } catch (e) {
                        // Support for test mock 401
                        if (args[0] === 'MOCK_401') {
                            window.dispatchEvent(new CustomEvent('titan-login-required'));
                        }
                        throw e;
                    }
                };

                window.addEventListener('titan-login-required', () => {
                    onReady(() => {
                        if (document.getElementById('titan-v5-auth-modal')) return;
                        const modal = document.createElement('div');
                        modal.id = 'titan-v5-auth-modal';
                        modal.innerHTML = `
                            <div class="titan-modal-backdrop" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1052;"></div>
                            <div class="titan-modal-content" style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#fff;padding:20px;border-radius:8px;z-index:1055;text-align:center;width:80%;max-width:300px;box-shadow: 0 4px 15px rgba(0,0,0,0.3); font-family: sans-serif;">
                                <p style="color:#333;font-weight:bold;margin-bottom:20px;">Error! Please login to start game.</p>
                                <button id="titan-login-primary" style="background:#00a826;color:#fff;border:none;padding:12px;border-radius:4px;margin-bottom:10px;width:100%;font-weight:bold;cursor:pointer;">Login</button>
                                <button id="titan-exit-secondary" style="background:#666;color:#fff;border:none;padding:12px;border-radius:4px;width:100%;font-weight:bold;cursor:pointer;">Exit</button>
                            </div>
                        `;
                        document.body.appendChild(modal);
                        document.getElementById('titan-login-primary').onclick = () => { window.location.href = '/ng/m/login'; };
                        document.getElementById('titan-exit-secondary').onclick = () => {
                            modal.remove();
                            if (window.history.length > 1) window.history.back();
                            else window.location.href = '/ng/m/home';
                        };
                    });
                });

                // 3. Dynamic Theme Detection & Styling
                const getTheme = () => {
                    let theme = document.documentElement.getAttribute('data-theme') || 'light';
                    if (theme === 'systemauto') {
                        theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                    }
                    return theme;
                };

                const updateLoaderStyles = () => {
                    const theme = getTheme();
                    const brand = window.BRAND_NAME || 'football';

                    const loaders = document.querySelectorAll('.app-init-loader-wrap, .m-loader, .loading-wrap, .m-loading-mask');
                    const spinners = document.querySelectorAll('.spinner-icon, .m-icon-loading');

                    loaders.forEach(loader => {
                        const targetColor = theme === 'light' ? '#f4f4f4' : ((brand === 'Encore') ? '#100e26' : '#000000');
                        if (loader.style.getPropertyValue('background-color') !== targetColor) {
                             loader.style.setProperty('background-color', targetColor, 'important');
                        }
                    });

                    if (theme === 'light') {
                        spinners.forEach(s => {
                            if (s.style.getPropertyValue('background-color') !== '#e0e1e2') {
                                s.style.setProperty('background-color', '#e0e1e2', 'important');
                            }
                        });
                    }
                };

                // 4. Z-Index Management & Loader Hiding
                let modalStack = 0;
                onReady(() => {
                    const observer = new MutationObserver(() => {
                        updateLoaderStyles();

                        if (document.querySelector('#app > *, .m-home > *, .m-game > *, #content > *')) {
                            const loaders = document.querySelectorAll('.app-init-loader-wrap, .m-loader, .loading-wrap');
                            loaders.forEach(l => {
                                if (l.style.getPropertyValue('display') !== 'none') {
                                    l.style.setProperty('display', 'none', 'important');
                                }
                            });
                        }

                        const backdrops = document.querySelectorAll('.modal-backdrop:not([data-managed]), .titan-modal-backdrop:not([data-managed])');
                        backdrops.forEach(b => {
                            b.style.zIndex = (1052 + (modalStack * 10)).toString();
                            b.setAttribute('data-managed', 'true');
                        });
                        const contents = document.querySelectorAll('.modal-content:not([data-managed]), .titan-modal-content:not([data-managed])');
                        contents.forEach(c => {
                            c.style.zIndex = (1055 + (modalStack * 10)).toString();
                            c.setAttribute('data-managed', 'true');
                            modalStack++;
                        });
                    });
                    observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });
                    updateLoaderStyles();
                });

                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateLoaderStyles);
            })();
        """)

    @staticmethod
    async def stabilize_environment(page: Page):
        """V5.34 CSS-NUKE & Stabilization: Hide traps via CSS injection."""
        print("DEBUG: Executing CSS-NUKE Stabilization...")
        try:
            # V5.34: Inject high-priority CSS to hide overlays and modals without breaking reactivity
            await page.add_style_tag(content="""
                .m-modal, .modal, .overlay, .modal-backdrop, [class*='backdrop']:not(.titan-modal-backdrop),
                [class*='overlay'], .dialog-wrap, .sg-confirm-cancel-modal-v2, .m-loading-mask,
                .app-loading, #app-loading {
                    display: none !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    z-index: -1 !important;
                    visibility: hidden !important;
                }
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
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('opacity', '0', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
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
