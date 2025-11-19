/**
 * Bold Flat Theme System - JavaScript Utilities
 * Handles theme switching, color customization, and localStorage persistence
 */

(function() {
    'use strict';

    // Theme Manager
    const ThemeManager = {
        // Get current theme from localStorage or default to 'light'
        getCurrentTheme: function() {
            return localStorage.getItem('boldFlatTheme') || 'light';
        },

        // Get current accent color from localStorage
        getCurrentAccentColor: function() {
            const theme = this.getCurrentTheme();
            const storageKey = theme === 'dark' ? 'boldFlatAccentDark' : 'boldFlatAccentLight';
            return localStorage.getItem(storageKey);
        },

        // Apply theme to document
        applyTheme: function(theme) {
            if (theme === 'dark') {
                document.body.classList.add('dark-theme');
            } else {
                document.body.classList.remove('dark-theme');
            }
            localStorage.setItem('boldFlatTheme', theme);
        },

        // Apply custom accent color
        applyAccentColor: function(color) {
            const theme = this.getCurrentTheme();
            const root = document.documentElement;
            
            // Calculate darker shades (simple approximation)
            const hexToRgb = (hex) => {
                const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                return result ? {
                    r: parseInt(result[1], 16),
                    g: parseInt(result[2], 16),
                    b: parseInt(result[3], 16)
                } : null;
            };

            const rgbToHex = (r, g, b) => {
                return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
            };

            const darken = (hex, percent) => {
                const rgb = hexToRgb(hex);
                if (!rgb) return hex;
                return rgbToHex(
                    Math.floor(rgb.r * percent),
                    Math.floor(rgb.g * percent),
                    Math.floor(rgb.b * percent)
                );
            };

            // Set CSS custom properties
            root.style.setProperty('--accent-primary', color);
            root.style.setProperty('--accent-dark', darken(color, 0.8));
            root.style.setProperty('--accent-darker', darken(color, 0.6));

            // Save to localStorage
            const storageKey = theme === 'dark' ? 'boldFlatAccentDark' : 'boldFlatAccentLight';
            localStorage.setItem(storageKey, color);
        },

        // Toggle between light and dark theme
        toggleTheme: function() {
            const currentTheme = this.getCurrentTheme();
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            this.applyTheme(newTheme);
            
            // Reapply saved accent color for new theme
            const accentColor = this.getCurrentAccentColor();
            if (accentColor) {
                this.applyAccentColor(accentColor);
            }
            
            return newTheme;
        },

        // Initialize theme on page load
        init: function() {
            const savedTheme = this.getCurrentTheme();
            this.applyTheme(savedTheme);
            
            const savedAccent = this.getCurrentAccentColor();
            if (savedAccent) {
                this.applyAccentColor(savedAccent);
            }
        }
    };

    // Preset color schemes
    const PRESET_COLORS = {
        light: {
            blue: { primary: '#3498db', dark: '#2980b9', darker: '#1f6391' },
            purple: { primary: '#9b59b6', dark: '#8e44ad', darker: '#6c3483' },
            green: { primary: '#2ecc71', dark: '#27ae60', darker: '#1e8449' },
            orange: { primary: '#e67e22', dark: '#d35400', darker: '#a04000' },
            pink: { primary: '#e91e63', dark: '#c2185b', darker: '#880e4f' },
            cyan: { primary: '#00bcd4', dark: '#0097a7', darker: '#00697c' },
            yellow: { primary: '#f1c40f', dark: '#f39c12', darker: '#d68910' }
        },
        dark: {
            red: { primary: '#ff3333', dark: '#cc0000', darker: '#990000' },
            purple: { primary: '#bb66ff', dark: '#9944dd', darker: '#7733bb' },
            green: { primary: '#00ff66', dark: '#00dd55', darker: '#00bb44' },
            orange: { primary: '#ff8833', dark: '#dd6611', darker: '#bb4400' },
            pink: { primary: '#ff3388', dark: '#dd1166', darker: '#bb0044' },
            cyan: { primary: '#00ddff', dark: '#00bbdd', darker: '#0099bb' },
            yellow: { primary: '#ffdd33', dark: '#ddbb11', darker: '#bb9900' }
        }
    };

    // Utility function to create theme toggle button
    window.createThemeToggle = function(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const currentTheme = ThemeManager.getCurrentTheme();
        const button = document.createElement('button');
        button.className = 'theme-toggle-btn';
        button.innerHTML = currentTheme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode';
        button.onclick = function() {
            const newTheme = ThemeManager.toggleTheme();
            button.innerHTML = newTheme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode';
        };
        container.appendChild(button);
    };

    // Utility function to create color picker
    window.createColorPicker = function(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const theme = ThemeManager.getCurrentTheme();
        const presets = PRESET_COLORS[theme];

        const pickerHTML = `
            <div class="color-picker">
                <label>Choose Accent Color:</label>
                <div class="color-presets">
                    ${Object.entries(presets).map(([name, colors]) => `
                        <button 
                            class="color-preset-btn" 
                            style="background: ${colors.primary};" 
                            data-color="${colors.primary}"
                            title="${name.charAt(0).toUpperCase() + name.slice(1)}"
                            onclick="window.applyPresetColor('${colors.primary}')">
                        </button>
                    `).join('')}
                </div>
                <input 
                    type="color" 
                    id="customColorPicker" 
                    value="${ThemeManager.getCurrentAccentColor() || presets.blue?.primary || presets.red?.primary}"
                    onchange="window.applyCustomColor(this.value)">
            </div>
        `;
        container.innerHTML = pickerHTML;
    };

    // Global functions for color application
    window.applyPresetColor = function(color) {
        ThemeManager.applyAccentColor(color);
    };

    window.applyCustomColor = function(color) {
        ThemeManager.applyAccentColor(color);
    };

    // Initialize theme when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            ThemeManager.init();
        });
    } else {
        ThemeManager.init();
    }

    // Export ThemeManager to window for external access
    window.BoldFlatTheme = ThemeManager;

})();
