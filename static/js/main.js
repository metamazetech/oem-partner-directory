// Utility to display notifications
function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '12px 24px';
    toast.style.borderRadius = '10px';
    toast.style.backgroundColor = isError ? 'rgba(239, 68, 68, 0.95)' : 'rgba(16, 185, 129, 0.95)';
    toast.style.color = 'white';
    toast.style.fontWeight = '600';
    toast.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.2)';
    toast.style.zIndex = '9999';
    toast.style.transition = 'all 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    toast.innerText = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 50);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Modal handling
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Set up event listeners on page load
document.addEventListener('DOMContentLoaded', () => {
    // 1. Client-side Search and Filter for Contacts
    const searchInput = document.getElementById('search-input');
    const filterSelect = document.getElementById('type-filter');
    const groupSelect = document.getElementById('group-filter');
    
    function filterCards() {
        const query = searchInput ? searchInput.value.toLowerCase() : '';
        const filterVal = filterSelect ? filterSelect.value : 'all';
        const groupVal = groupSelect ? groupSelect.value : 'all';
        const isSearchingOrFiltering = query !== '' || filterVal !== 'all' || groupVal !== 'all';
        
        const categoryGroups = document.querySelectorAll('.category-group');
        categoryGroups.forEach(groupBlock => {
            const contentDiv = groupBlock.querySelector('.category-content');
            const countBadge = groupBlock.querySelector('.category-count');
            const cards = groupBlock.querySelectorAll('.contact-card');
            
            let visibleCardsInGroup = 0;
            
            cards.forEach(card => {
                const company = card.getAttribute('data-company').toLowerCase();
                const name = card.getAttribute('data-name').toLowerCase();
                const type = card.getAttribute('data-type');
                const group = card.getAttribute('data-group') || 'Other';
                const portfolio = (card.getAttribute('data-portfolio') || '').toLowerCase();
                
                const matchesQuery = company.includes(query) || name.includes(query) || portfolio.includes(query);
                const matchesType = filterVal === 'all' || type === filterVal;
                const matchesGroup = groupVal === 'all' || group.toLowerCase() === groupVal.toLowerCase();
                
                if (matchesQuery && matchesType && matchesGroup) {
                    card.style.display = 'flex';
                    visibleCardsInGroup++;
                } else {
                    card.style.display = 'none';
                }
            });
            
            if (countBadge) {
                countBadge.innerText = visibleCardsInGroup;
            }
            
            if (visibleCardsInGroup > 0) {
                groupBlock.style.display = 'block';
                if (isSearchingOrFiltering) {
                    groupBlock.classList.add('expanded');
                    if (contentDiv) contentDiv.style.display = 'grid';
                } else {
                    groupBlock.classList.remove('expanded');
                    if (contentDiv) contentDiv.style.display = 'none';
                }
            } else {
                groupBlock.style.display = 'none';
            }
        });
    }
    
    if (searchInput) searchInput.addEventListener('input', filterCards);
    if (filterSelect) filterSelect.addEventListener('change', filterCards);
    if (groupSelect) groupSelect.addEventListener('change', filterCards);
    
    // 2. Setup Modals close events
    const closeButtons = document.querySelectorAll('.modal-close, .btn-close-modal');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal-backdrop');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });
    
    // Close modal if clicked outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-backdrop')) {
            closeModal(e.target.id);
        }
    });
    
    initExportInterceptors();
});

// Trigger AJAX Website Scraper on OEM detail page
function triggerWebsiteScrape(contactId) {
    const btn = document.getElementById('btn-scrape-site');
    const productsList = document.getElementById('fetched-products-list');
    const servicesList = document.getElementById('fetched-services-list');
    const metaContainer = document.getElementById('scrape-meta-container');
    const statusMsg = document.getElementById('scrape-status-text');
    
    if (!btn) return;
    
    const origHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> <span class="loading-text">Scraping website...</span>';
    
    fetch(getAppUrl(`/contact/${contactId}/scrape`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
        
        if (data.status === 'success' || data.status === 'partial') {
            showToast('Website crawl completed!');
            
            if (metaContainer) {
                metaContainer.innerHTML = `
                    <p style="font-size: 0.8rem; color: var(--text-muted);">
                        Last auto-crawl loaded from: <a href="${data.url || '#'}" target="_blank" style="color:var(--primary);">${data.title || 'Website'} 🔗</a>
                    </p>
                `;
            }
            
            if (statusMsg) {
                statusMsg.className = `scrape-status-message ${data.status}`;
                statusMsg.innerHTML = data.status === 'success' 
                    ? '<strong>Crawl Status:</strong> Success. Extracted directly from website.' 
                    : `<strong>Crawl Status:</strong> Partial. Using default pre-sales profile suggestions (Web site blocked scraping).`;
            }
            
            // 1. Repopulate Products, keeping MANUAL custom ones
            if (productsList) {
                const manualProducts = Array.from(productsList.querySelectorAll('li[data-item-source="custom"]')).map(li => li.getAttribute('data-item-val'));
                productsList.innerHTML = '';
                
                // Add new auto products
                if (data.products && data.products.length > 0) {
                    data.products.forEach(p => {
                        const li = document.createElement('li');
                        li.className = 'portfolio-item';
                        li.setAttribute('data-item-val', p);
                        li.setAttribute('data-item-source', 'fetched');
                        li.innerHTML = `
                            <span style="display:flex; align-items:center; gap:0.5rem;">
                                <span style="font-size:0.65rem; padding:0.1rem 0.3rem; background:rgba(16,185,129,0.15); color:var(--color-oem); border-radius:4px; font-weight:700; letter-spacing:0.02em;">AUTO</span>
                                ${escapeHtml(p)}
                            </span>
                            <span class="item-delete-btn" onclick="deletePortfolioItem(${contactId}, 'product', 'fetched', '${escapeQuotes(p)}')">🗑️</span>
                        `;
                        productsList.appendChild(li);
                    });
                }
                
                // Append manual products back
                manualProducts.forEach(p => {
                    const li = document.createElement('li');
                    li.className = 'portfolio-item';
                    li.setAttribute('data-item-val', p);
                    li.setAttribute('data-item-source', 'custom');
                    li.innerHTML = `
                        <span style="display:flex; align-items:center; gap:0.5rem;">
                            <span style="font-size:0.65rem; padding:0.1rem 0.3rem; background:rgba(99,102,241,0.15); color:var(--primary); border-radius:4px; font-weight:700; letter-spacing:0.02em;">MANUAL</span>
                            ${escapeHtml(p)}
                        </span>
                        <span class="item-delete-btn" onclick="deletePortfolioItem(${contactId}, 'product', 'custom', '${escapeQuotes(p)}')">🗑️</span>
                    `;
                    productsList.appendChild(li);
                });
                
                if (productsList.children.length === 0) {
                    productsList.innerHTML = '<li class="portfolio-item placeholder-item"><span>No products listed yet.</span></li>';
                }
            }
            
            // 2. Repopulate Services, keeping MANUAL custom ones
            if (servicesList) {
                const manualServices = Array.from(servicesList.querySelectorAll('li[data-item-source="custom"]')).map(li => li.getAttribute('data-item-val'));
                servicesList.innerHTML = '';
                
                // Add new auto services
                if (data.services && data.services.length > 0) {
                    data.services.forEach(s => {
                        const li = document.createElement('li');
                        li.className = 'portfolio-item';
                        li.setAttribute('data-item-val', s);
                        li.setAttribute('data-item-source', 'fetched');
                        li.innerHTML = `
                            <span style="display:flex; align-items:center; gap:0.5rem;">
                                <span style="font-size:0.65rem; padding:0.1rem 0.3rem; background:rgba(59,130,246,0.15); color:var(--color-distributor); border-radius:4px; font-weight:700; letter-spacing:0.02em;">AUTO</span>
                                ${escapeHtml(s)}
                            </span>
                            <span class="item-delete-btn" onclick="deletePortfolioItem(${contactId}, 'service', 'fetched', '${escapeQuotes(s)}')">🗑️</span>
                        `;
                        servicesList.appendChild(li);
                    });
                }
                
                // Append manual services back
                manualServices.forEach(s => {
                    const li = document.createElement('li');
                    li.className = 'portfolio-item';
                    li.setAttribute('data-item-val', s);
                    li.setAttribute('data-item-source', 'custom');
                    li.innerHTML = `
                        <span style="display:flex; align-items:center; gap:0.5rem;">
                            <span style="font-size:0.65rem; padding:0.1rem 0.3rem; background:rgba(99,102,241,0.15); color:var(--primary); border-radius:4px; font-weight:700; letter-spacing:0.02em;">MANUAL</span>
                            ${escapeHtml(s)}
                        </span>
                        <span class="item-delete-btn" onclick="deletePortfolioItem(${contactId}, 'service', 'custom', '${escapeQuotes(s)}')">🗑️</span>
                    `;
                    servicesList.appendChild(li);
                });
                
                if (servicesList.children.length === 0) {
                    servicesList.innerHTML = '<li class="portfolio-item placeholder-item"><span>No services listed yet.</span></li>';
                }
            }
        } else {
            showToast(data.message || 'Scrape failed', true);
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
        showToast('Error connecting to scraper server', true);
        console.error(err);
    });
}

// Add Custom Portfolio Item (Product or Service)
function addCustomItem(contactId, itemType) {
    const input = document.getElementById(`new-custom-${itemType}-input`);
    const list = document.getElementById(`fetched-${itemType}s-list`);
    
    if (!input || !input.value.trim()) return;
    
    const value = input.value.trim();
    
    fetch(getAppUrl(`/contact/${contactId}/custom-item`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            type: itemType,
            value: value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            input.value = '';
            showToast(`Manual ${itemType} added!`);
            
            // Remove placeholder if present
            const placeholder = list.querySelector('.placeholder-item');
            if (placeholder) placeholder.remove();
            
            // Append to list dynamically
            const li = document.createElement('li');
            li.className = 'portfolio-item';
            li.setAttribute('data-item-val', value);
            li.setAttribute('data-item-source', 'custom');
            li.innerHTML = `
                <span style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:0.65rem; padding:0.1rem 0.3rem; background:rgba(99,102,241,0.15); color:var(--primary); border-radius:4px; font-weight:700; letter-spacing:0.02em;">MANUAL</span>
                    ${escapeHtml(value)}
                </span>
                <span class="item-delete-btn" onclick="deletePortfolioItem(${contactId}, '${itemType}', 'custom', '${escapeQuotes(value)}')">🗑️</span>
            `;
            list.appendChild(li);
        } else {
            showToast(data.message || 'Failed to add item', true);
        }
    })
    .catch(err => {
        showToast('Error saving item', true);
        console.error(err);
    });
}

// Delete Portfolio Item (Unified Scraped or Custom)
function deletePortfolioItem(contactId, itemType, source, value) {
    if (!solveMathPuzzle(`Are you sure you want to delete "${value}"?`)) return;
    
    fetch(getAppUrl(`/contact/${contactId}/portfolio/delete`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            type: itemType,
            source: source,
            value: value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('Item deleted.');
            
            // Remove from DOM
            const escaped = escapeQuotes(value);
            const li = document.querySelector(`#fetched-${itemType}s-list li[data-item-val="${escaped}"][data-item-source="${source}"]`);
            if (li) {
                const parent = li.parentNode;
                li.remove();
                if (parent.children.length === 0) {
                    parent.innerHTML = '<li class="portfolio-item placeholder-item"><span>No items listed yet.</span></li>';
                }
            } else {
                window.location.reload();
            }
        } else {
            showToast(data.message || 'Failed to delete item', true);
        }
    })
    .catch(err => {
        showToast('Error deleting item', true);
        console.error(err);
    });
}

// Helper to escape HTML tags
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

// Helper to escape quotes for JS string matching in selectors
function escapeQuotes(str) {
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// Mobile nav menu toggle listener
document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.getElementById('mobile-nav-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (navToggle && sidebar) {
        navToggle.addEventListener('click', () => {
            sidebar.classList.toggle('menu-open');
            navToggle.innerHTML = sidebar.classList.contains('menu-open') ? '✕' : '☰';
        });
    }
});

// Dynamic Contact Rows generation for forms
function addContactRow(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const row = document.createElement('div');
    row.className = 'contact-person-row';
    row.style.background = 'rgba(255,255,255,0.01)';
    row.style.border = '1px solid var(--border-glass)';
    row.style.padding = '1rem';
    row.style.borderRadius = '8px';
    row.style.marginBottom = '1rem';
    row.style.position = 'relative';
    
    row.innerHTML = `
        <button type="button" class="btn-remove-person" onclick="this.closest('.contact-person-row').remove()" style="position: absolute; top: 0.5rem; right: 0.5rem; background: none; border: none; color: var(--color-alert); font-size: 1.25rem; cursor: pointer; line-height: 1;">✕</button>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Contact Person Name*</label>
                <input type="text" name="contact_name[]" class="form-control" placeholder="e.g. Rahul Sharma" required>
            </div>
            <div class="form-group">
                <label class="form-label">Designation</label>
                <input type="text" name="contact_designation[]" class="form-control" placeholder="e.g. Channel Manager">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" name="contact_email[]" class="form-control" placeholder="rahul@cisco.com">
            </div>
            <div class="form-group">
                <label class="form-label">Phone / Mobile</label>
                <input type="text" name="contact_phone[]" class="form-control" placeholder="+91 98765 43210">
            </div>
        </div>
    `;
    container.appendChild(row);
}

// WhatsApp sharing generator
function shareOnWhatsApp(company, name, designation, phone, email, website) {
    let text = `*Contact Details for ${company}:*\n`;
    text += `👤 *Name:* ${name}\n`;
    if (designation) text += `💼 *Designation:* ${designation}\n`;
    if (phone) text += `📞 *Phone:* ${phone}\n`;
    if (email) text += `✉️ *Email:* ${email}\n`;
    if (website) text += `🌐 *Website:* ${website}\n`;
    
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

// Open Edit Interaction Modal for Admins
function openEditInteractionModal(contactId, id, date, typeStr, summary, nextSteps, followupDate) {
    const modal = document.getElementById('edit-interaction-modal');
    const form = document.getElementById('edit-interaction-form');
    if (!modal || !form) return;
    
    form.action = `/contact/${contactId}/interaction/${id}/edit`;
    document.getElementById('edit_interaction_date').value = date;
    document.getElementById('edit_summary').value = summary;
    document.getElementById('edit_next_steps').value = nextSteps;
    document.getElementById('edit_followup_date').value = followupDate;
    
    const types = typeStr.split(',').map(s => s.trim().toLowerCase());
    const checkboxes = document.querySelectorAll('.edit-type-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = types.includes(cb.value.toLowerCase());
    });
    
    openModal('edit-interaction-modal');
}

// ==========================================
// Entry Mode Toggle & Unified Scanning (QR & OCR)
// ==========================================

// Global switch mode tabs handler
function switchAddMode(mode) {
    const btnManual = document.getElementById('btn-mode-manual');
    const btnScan = document.getElementById('btn-mode-scan');
    const manualFields = document.getElementById('manual-entry-form-fields');
    const scanPanel = document.getElementById('add-mode-scan-panel');
    
    if (mode === 'manual') {
        if (btnManual) {
            btnManual.classList.remove('btn-secondary');
            btnManual.classList.add('btn-primary');
        }
        if (btnScan) {
            btnScan.classList.remove('btn-primary');
            btnScan.classList.add('btn-secondary');
        }
        if (manualFields) manualFields.style.display = 'block';
        if (scanPanel) scanPanel.style.display = 'none';
    } else {
        if (btnManual) {
            btnManual.classList.remove('btn-primary');
            btnManual.classList.add('btn-secondary');
        }
        if (btnScan) {
            btnScan.classList.remove('btn-secondary');
            btnScan.classList.add('btn-primary');
        }
        if (manualFields) manualFields.style.display = 'none';
        if (scanPanel) scanPanel.style.display = 'block';
    }
}

// Trigger QR Scan File Upload
function handleCardScanFile(input) {
    const file = input.files[0];
    if (!file) return;
    
    // Auto-bind front card file
    const addCardFrontInput = document.getElementById('add_visiting_card_front');
    if (addCardFrontInput) {
        // Use DataTransfer to programmatically bind file to form upload
        const container = new DataTransfer();
        container.items.add(file);
        addCardFrontInput.files = container.files;
        showToast("📸 Card file auto-bound to Front Visiting Card field.");
    }
    
    // Show status indicator
    const statusIndicator = document.getElementById('ocr-scan-status-indicator');
    const statusText = document.getElementById('ocr-scan-status-text');
    if (statusIndicator) statusIndicator.style.display = 'block';
    if (statusText) statusText.innerText = "Uploading & analyzing card...";
    
    // Send to backend /scan-card route
    const formData = new FormData();
    formData.append('card_image', file);
    
    fetch(getAppUrl('/scan-card'), {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(resJson => {
        if (resJson.status === 'success') {
            const data = resJson.data;
            
            // Auto populate form
            if (data.company_name) document.getElementById('company_name').value = data.company_name;
            if (data.website) {
                document.getElementById('website').value = data.website;
                // Trigger auto-fetch logo preview
                const logoContainer = document.getElementById('company-logo-container');
                const domain = getDomainFromUrl(data.website);
                if (domain && logoContainer) {
                    logoContainer.innerHTML = `<img src="https://logo.clearbit.com/${domain}" alt="Logo" style="width: 100%; height: 100%; object-fit: contain; background: white;" onerror="this.parentElement.innerHTML='🌐';">`;
                }
            }
            if (data.address) document.getElementById('address').value = data.address;
            
            // For contacts list (the first one)
            const nameInputs = document.getElementsByName('contact_name[]');
            const desigInputs = document.getElementsByName('contact_designation[]');
            const emailInputs = document.getElementsByName('contact_email[]');
            const phoneInputs = document.getElementsByName('contact_phone[]');
            
            if (nameInputs.length > 0 && data.name) nameInputs[0].value = data.name;
            if (desigInputs.length > 0 && data.designation) desigInputs[0].value = data.designation;
            if (emailInputs.length > 0 && data.email) emailInputs[0].value = data.email;
            if (phoneInputs.length > 0 && data.phone) phoneInputs[0].value = data.phone;
            
            showToast("✅ Card successfully analyzed and fields populated!");
        } else if (resJson.status === 'fallback') {
            if (statusText) statusText.innerText = "Running local client-side OCR...";
            // Fallback: Run Tesseract.js client side
            const reader = new FileReader();
            reader.onload = function(event) {
                runOCROnImage(event.target.result);
            };
            reader.readAsDataURL(file);
            return;
        } else {
            alert("Error parsing card: " + resJson.message);
        }
        if (statusIndicator) statusIndicator.style.display = 'none';
    })
    .catch(err => {
        console.error("Card scan error:", err);
        // Fallback: Run Tesseract.js client side
        if (statusText) statusText.innerText = "Running local client-side OCR (Fallback)...";
        const reader = new FileReader();
        reader.onload = function(event) {
            runOCROnImage(event.target.result);
        };
        reader.readAsDataURL(file);
    });
}

// Execute OCR processing via Tesseract.js loaded from CDN
function runOCROnImage(imageSrc) {
    if (typeof Tesseract === 'undefined') {
        alert("OCR Engine is loading from CDN. Please wait a few seconds and try again.");
        return;
    }
    
    const statusText = document.getElementById('ocr-scan-status-text');
    const statusIndicator = document.getElementById('ocr-scan-status-indicator');
    if (statusIndicator) statusIndicator.style.display = 'block';
    if (statusText) statusText.innerText = "Initializing OCR Engine...";
    
    // Dynamically query selected OCR language(s)
    const langSelect = document.getElementById('ocr-lang-select');
    const selectedLang = langSelect ? langSelect.value : 'eng';
    
    Tesseract.recognize(
        imageSrc,
        selectedLang,
        { logger: m => {
            if (statusText && m.status === 'recognizing') {
                statusText.innerText = `Recognizing text (${selectedLang}): ${Math.round(m.progress * 100)}%`;
            }
        }}
    ).then(({ data: { text } }) => {
        if (statusIndicator) statusIndicator.style.display = 'none';
        parseOCRVendorInfo(text);
    }).catch(err => {
        console.error("Tesseract OCR Error:", err);
        if (statusIndicator) statusIndicator.style.display = 'none';
        alert("❌ OCR Scan Failed: Could not parse business card text.");
    });
}

// Heuristics parser to map raw OCR text into vendor contact fields
function parseOCRVendorInfo(text) {
    if (!text) return;
    
    console.log("Raw business card text:", text);
    
    // Clean up lines and drop non-alphanumeric noise lines (junk characters)
    const lines = text.split('\n').map(l => {
        // Remove noise/shapes characters but keep text, standard punctuation, and symbols for email/url
        return l.replace(/[\|\[\]\{\}\(\)\<\>\#\$\%\^\&\*\_\\\/°¢€¥©®™•■□▲▼♦♥♣♠~`—\-–—]+/g, '').trim();
    }).filter(l => {
        if (l.length < 3) return false;
        // Count letters and digits to test character density
        const cleanAlphanumeric = l.replace(/[^a-zA-Z0-9]/g, '');
        const density = cleanAlphanumeric.length / l.length;
        // Keep lines that have at least 3 letters/digits and an alphanumeric density > 40%
        return cleanAlphanumeric.length >= 3 && density > 0.4;
    });
    
    let name = '';
    let designation = '';
    let email = '';
    let phone = '';
    let website = '';
    let company = '';
    let address = '';
    let addressLines = [];
    
    // 1. Email Extraction
    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/i;
    const emailMatch = text.match(emailRegex);
    if (emailMatch) {
        email = emailMatch[0];
    }
    
    // 2. Phone Extraction
    const phoneRegex = /(?:mob|tel|phone|ph|contact|call)?\s*(?:[+:\s]*\d{1,4}[-\s]*)?(?:\d{3,5}[-\s]*)?\d{3,4}[-\s]*\d{3,4}/gi;
    const phoneMatches = text.match(phoneRegex);
    if (phoneMatches) {
        for (let match of phoneMatches) {
            const digits = match.replace(/\D/g, '');
            if (digits.length >= 8 && digits.length <= 15) {
                phone = match.replace(/^(?:mob|tel|phone|ph|contact|call)[\s:]*/i, '').trim();
                break;
            }
        }
    }
    
    // 3. Website Extraction
    const urlRegex = /(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})(\/[a-zA-Z0-9-_./]*)?/i;
    const urlMatches = text.match(urlRegex);
    if (urlMatches) {
        for (let match of urlMatches) {
            const matchStr = match[0];
            if (matchStr.includes('@')) continue;
            website = matchStr;
            if (!website.startsWith('http://') && !website.startsWith('https://')) {
                website = 'https://' + website;
            }
            break;
        }
    }
    
    // 4. Designation & Name Heuristics
    const designKeywords = [
        'manager', 'director', 'engineer', 'head', 'lead', 'executive', 'officer', 'consultant',
        'sales', 'marketing', 'founder', 'ceo', 'cto', 'coo', 'vp', 'president', 'partner', 'specialist',
        'architect', 'developer', 'representative'
    ];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes('@') || line.toLowerCase().includes('.com') || line.toLowerCase().includes('.org') || line.toLowerCase().includes('.net')) {
            continue;
        }
        
        const lowercaseLine = line.toLowerCase();
        let isDesignation = false;
        for (let keyword of designKeywords) {
            if (lowercaseLine.includes(keyword)) {
                designation = line;
                isDesignation = true;
                break;
            }
        }
        
        if (isDesignation) {
            if (i > 0 && !name) {
                const prevLine = lines[i-1];
                if (!prevLine.match(/\d{5,}/) && prevLine.length < 40) {
                    name = prevLine;
                }
            }
            continue;
        }
        
        // Address heuristics keywords
        const addrKeywords = ['road', 'rd', 'street', 'st', 'bldg', 'building', 'floor', 'flr', 'office', 'suite', 'block', 'city', 'nagar', 'colony', 'industrial', 'phase', 'sector', 'pin', 'postal', 'india', 'state'];
        let isAddress = false;
        for (let kw of addrKeywords) {
            if (lowercaseLine.includes(kw)) {
                isAddress = true;
                break;
            }
        }
        if (isAddress) {
            addressLines.push(line);
        }
    }
    
    // Fallback for contact person name
    if (!name && lines.length > 0) {
        for (let line of lines) {
            if (!line.match(/\d/) && !line.includes('@') && line.length < 35 && line.length > 3) {
                name = line;
                break;
            }
        }
    }
    
    // Company Name heuristics from email domain
    if (email) {
        const domainParts = email.split('@')[1].split('.');
        if (domainParts.length > 1) {
            const domainName = domainParts[0].toLowerCase();
            const commonProviders = ['gmail', 'yahoo', 'hotmail', 'outlook', 'protonmail', 'icloud', 'aol'];
            if (!commonProviders.includes(domainName)) {
                company = domainName.charAt(0).toUpperCase() + domainName.slice(1);
            }
        }
    }
    
    if (!company && lines.length > 0) {
        const firstLine = lines[0];
        if (firstLine !== name && firstLine.length < 40) {
            company = firstLine;
        }
    }
    
    if (addressLines.length > 0) {
        address = addressLines.join(', ');
    }
    
    // Populate manual entry inputs
    const compInput = document.getElementById('company_name');
    const webInput = document.getElementById('website');
    const addrInput = document.getElementById('address');
    
    if (compInput && company) compInput.value = company;
    if (webInput && website) webInput.value = website;
    if (addrInput && address) addrInput.value = address;
    
    const nameInput = document.querySelector('#add-contact-persons-container input[name="contact_name[]"]');
    const desigInput = document.querySelector('#add-contact-persons-container input[name="contact_designation[]"]');
    const emailInput = document.querySelector('#add-contact-persons-container input[name="contact_email[]"]');
    const phoneInput = document.querySelector('#add-contact-persons-container input[name="contact_phone[]"]');
    
    if (nameInput && name) nameInput.value = name;
    if (desigInput && designation) desigInput.value = designation;
    if (emailInput && email) emailInput.value = email;
    if (phoneInput && phone) phoneInput.value = phone;
    
    // Switch to manual mode and display warning alerts to check
    switchAddMode('manual');
    showToast("🎉 Business card parsed! Check fields below.");
}

// Hook up Front card image upload QR/OCR scanning
const addCardFrontInput = document.getElementById('add_visiting_card_front');
if (addCardFrontInput) {
    addCardFrontInput.addEventListener('change', function(e) {
        handleCardScanFile(this);
    });
}

// Parse QR code content (vCard format or website URL) and auto-populate form
function parseQRContactInfo(text) {
    if (!text) return;
    
    // Check if it's a URL
    if (text.startsWith('http://') || text.startsWith('https://')) {
        const webInput = document.getElementById('website');
        if (webInput) webInput.value = text;
        alert("🔗 Scanned QR Code Website: " + text);
        return;
    }
    
    if (!text.toUpperCase().includes('BEGIN:VCARD')) {
        // Fallback for plain text codes
        alert("📝 Scanned QR Code Text: " + text);
        return;
    }
    
    // Parse vCard format lines
    const lines = text.split(/\r?\n/);
    let name = '';
    let company = '';
    let designation = '';
    let email = '';
    let phone = '';
    let website = '';
    let address = '';
    
    lines.forEach(line => {
        const parts = line.split(':');
        if (parts.length < 2) return;
        const key = parts[0].toUpperCase();
        const value = parts.slice(1).join(':').trim();
        
        if (key.startsWith('FN')) {
            name = value;
        } else if (key.startsWith('N') && !name) {
            const nParts = value.split(';');
            if (nParts.length > 1) {
                name = (nParts[1] + ' ' + nParts[0]).trim();
            } else {
                name = value.replace(/;/g, ' ').trim();
            }
        } else if (key.startsWith('ORG')) {
            company = value.split(';')[0].trim();
        } else if (key.startsWith('TITLE')) {
            designation = value;
        } else if (key.startsWith('TEL')) {
            phone = value;
        } else if (key.startsWith('EMAIL')) {
            email = value;
        } else if (key.startsWith('URL')) {
            website = value;
        } else if (key.startsWith('ADR')) {
            address = value.replace(/;/g, ' ').trim();
        }
    });
    
    // Autofill main partner details
    const compInput = document.getElementById('company_name');
    const webInput = document.getElementById('website');
    const addrInput = document.getElementById('address');
    
    if (compInput && company) compInput.value = company;
    if (webInput && website) webInput.value = website;
    if (addrInput && address) addrInput.value = address;
    
    // Autofill primary contact (the first contact person row in the dynamic container)
    const nameInput = document.querySelector('#add-contact-persons-container input[name="contact_name[]"]');
    const desigInput = document.querySelector('#add-contact-persons-container input[name="contact_designation[]"]');
    const emailInput = document.querySelector('#add-contact-persons-container input[name="contact_email[]"]');
    const phoneInput = document.querySelector('#add-contact-persons-container input[name="contact_phone[]"]');
    
    if (nameInput && name) nameInput.value = name;
    if (desigInput && designation) desigInput.value = designation;
    if (emailInput && email) emailInput.value = email;
    if (phoneInput && phone) phoneInput.value = phone;
    
    alert("🎉 Scanned QR code containing vCard! Fields have been auto-filled.");
}

function getAppUrl(path) {
    const cleanPath = path.startsWith('/') ? path.substring(1) : path;
    const base = window.BASE_URL || '/';
    const cleanBase = base.endsWith('/') ? base : base + '/';
    return cleanBase + cleanPath;
}

// ==========================================
// Category Navigation & URL Parsing
// ==========================================

function filterByCategory(category) {
    const groupFilter = document.getElementById('group-filter');
    if (groupFilter) {
        groupFilter.value = category;
        // Trigger filter event
        const event = new Event('change');
        groupFilter.dispatchEvent(event);
        
        // Highlight active sidebar selector
        document.querySelectorAll('.category-item').forEach(item => {
            if (item.getAttribute('data-category').toLowerCase() === category.toLowerCase()) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    } else {
        // Redirect to dashboard with query param
        window.location.href = getAppUrl('/?group=' + encodeURIComponent(category));
    }
}

// Check URL params on load for query filtering
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const groupParam = urlParams.get('group');
    if (groupParam) {
        setTimeout(() => {
            filterByCategory(groupParam);
        }, 120);
    }
});

// ==========================================
// Progress Bar & AJAX CSV Operations
// ==========================================

function showProgressOverlay(title, initialText) {
    let overlay = document.getElementById('progress-bar-overlay');
    if (overlay) overlay.remove();
    
    overlay = document.createElement('div');
    overlay.id = 'progress-bar-overlay';
    overlay.className = 'progress-overlay';
    overlay.innerHTML = `
        <div class="progress-title">${title}</div>
        <div class="progress-container">
            <div id="progress-bar-fill" class="progress-bar" style="width: 0%;"></div>
        </div>
        <div id="progress-bar-text" class="progress-text">${initialText}</div>
    `;
    document.body.appendChild(overlay);
}

function updateProgressBar(percent, text) {
    const fill = document.getElementById('progress-bar-fill');
    const txt = document.getElementById('progress-bar-text');
    if (fill) fill.style.width = percent + '%';
    if (txt && text) txt.textContent = text;
}

function hideProgressOverlay() {
    const overlay = document.getElementById('progress-bar-overlay');
    if (overlay) overlay.remove();
}

// Bind CSV imports with progress bar
document.addEventListener('DOMContentLoaded', () => {
    const csvFileInput = document.getElementById('csv-import-file');
    if (csvFileInput) {
        csvFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(event) {
                const text = event.target.result;
                const rows = text.split(/\r?\n/);
                if (rows.length <= 1) {
                    alert("❌ CSV file is empty.");
                    csvFileInput.value = '';
                    return;
                }
                
                // Parse headers
                const headers = rows[0].split(',').map(h => h.replace(/^["']|["']$/g, '').trim());
                let groupIdx = headers.indexOf('OEM Group');
                if (groupIdx === -1) {
                    groupIdx = 2; // Fallback to column index 2
                }
                
                // Collect unique categories
                const uniqueGroups = new Set();
                for (let i = 1; i < rows.length; i++) {
                    const row = rows[i].trim();
                    if (!row) continue;
                    
                    // Basic split by comma, ignoring commas in quotes
                    let cols = [];
                    let insideQuote = false;
                    let currentField = '';
                    for (let char of row) {
                        if (char === '"' || char === "'") {
                            insideQuote = !insideQuote;
                        } else if (char === ',' && !insideQuote) {
                            cols.push(currentField.trim());
                            currentField = '';
                        } else {
                            currentField += char;
                        }
                    }
                    cols.push(currentField.trim());
                    
                    if (cols.length > groupIdx) {
                        const gName = cols[groupIdx].replace(/^["']|["']$/g, '').trim();
                        if (gName && gName.toLowerCase() !== 'other') {
                            uniqueGroups.add(gName);
                        }
                    }
                }
                
                // Get existing categories from page (sidebar category-item data-category)
                const existingGroups = new Set();
                document.querySelectorAll('.category-item').forEach(el => {
                    const catName = el.getAttribute('data-category');
                    if (catName) existingGroups.add(catName.toLowerCase());
                });
                
                // Confirm each missing category
                const missingArray = Array.from(uniqueGroups).filter(g => !existingGroups.has(g.toLowerCase()));
                if (missingArray.length > 0) {
                    const missingList = missingArray.join(', ');
                    const confirmCreate = confirm(`⚠️ The following categories do not exist in the system:\n   [ ${missingList} ]\n\nClick OK to automatically create these categories and continue importing, or Cancel to abort.`);
                    if (!confirmCreate) {
                        csvFileInput.value = '';
                        return;
                    }
                }
                
                // Proceed to upload
                uploadCSVFile(file);
            };
            reader.readAsText(file);
        });
    }
});

function uploadCSVFile(file) {
    showProgressOverlay("Importing CSV Database", "Uploading files and analyzing headers...");
    
    const formData = new FormData();
    formData.append('csv_file', file);
    
    const xhr = new XMLHttpRequest();
    xhr.open('POST', getAppUrl('/import/csv'), true);
    
    xhr.upload.addEventListener('progress', function(event) {
        if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            const displayPercent = Math.min(Math.round(percent * 0.9), 90);
            updateProgressBar(displayPercent, `Uploading data: ${displayPercent}%`);
        }
    });
            
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4) {
                    let responseJson = null;
                    try {
                        responseJson = JSON.parse(xhr.responseText);
                    } catch (e) {
                        console.error("JSON parsing error:", e);
                    }
                    
                    if (xhr.status === 200 && responseJson && responseJson.status === 'success') {
                        updateProgressBar(95, "Resolving names and fetching company logos...");
                        setTimeout(() => {
                            updateProgressBar(100, "Import complete! Generating report summary...");
                            setTimeout(() => {
                                hideProgressOverlay();
                                
                                // Build Summary Report HTML
                                let summaryHtml = `
                                    <div style="text-align: left; font-family: var(--font-sans); color: white;">
                                        <div style="font-size: 1.2rem; font-weight: 800; margin-bottom: 1rem; color: var(--primary); display: flex; align-items: center; gap: 0.5rem;">
                                            <span>📊</span> CSV Import Summary Report
                                        </div>
                                        <p style="font-size: 0.9rem; margin-bottom: 1rem; color: var(--text-secondary); line-height: 1.4;">
                                            ${escapeHtml(responseJson.message)}
                                        </p>
                                `;
                                
                                if (responseJson.warnings && responseJson.warnings.length > 0) {
                                    summaryHtml += `
                                        <div style="margin-top: 1rem;">
                                            <div style="font-size: 0.85rem; font-weight: 700; color: #fbcfe8; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.25rem;">
                                                <span>⚠️</span> Activity Log & Warning Messages (${responseJson.warnings.length}):
                                            </div>
                                            <ul style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-glass); border-radius: 8px; padding: 0.75rem 1rem; max-height: 180px; overflow-y: auto; font-size: 0.85rem; line-height: 1.5; color: var(--text-secondary); margin: 0; list-style-type: disc; padding-left: 1.5rem;">
                                    `;
                                    responseJson.warnings.forEach(w => {
                                        summaryHtml += `<li style="margin-bottom: 0.35rem;">${escapeHtml(w)}</li>`;
                                    });
                                    summaryHtml += `
                                            </ul>
                                        </div>
                                    `;
                                } else {
                                    summaryHtml += `
                                        <div style="margin-top: 1rem; font-size: 0.85rem; color: #34d399; display: flex; align-items: center; gap: 0.25rem; font-weight: 600;">
                                            <span>✅</span> Database Sync Success: All rows parsed cleanly with no warnings.
                                        </div>
                                    `;
                                }
                                
                                summaryHtml += `
                                        <div style="display: flex; justify-content: flex-end; margin-top: 1.5rem;">
                                            <button id="btn-close-import-summary" class="btn btn-primary" style="padding: 0.5rem 1.5rem; font-size: 0.85rem; border-radius: 8px;">OK, Refresh Directory</button>
                                        </div>
                                    </div>
                                `;
                                
                                showCustomModalDialog(summaryHtml, () => {
                                    window.location.reload();
                                });
                            }, 800);
                        }, 1200);
                    } else {
                        hideProgressOverlay();
                        csvFileInput.value = ''; // Reset input to allow re-upload
                        console.error("CSV Import failed. HTTP Status:", xhr.status);
                        console.error("Server Response Raw Text:", xhr.responseText);
                        
                        const errorMsg = (responseJson && responseJson.message) ? responseJson.message : `Server Error (HTTP ${xhr.status}). If you just uploaded the new files, please click 'Restart' on your cPanel Python Application Manager to apply the updates.`;
                        alert("❌ CSV Import Failed:\n\n" + errorMsg);
                    }
                }
            };
            
            xhr.send(formData);
}

// Bind CSV exports with visual progress feedback
function handleCSVExport(event) {
    event.preventDefault();
    const exportUrl = event.currentTarget.getAttribute('href');
    
    showProgressOverlay("Exporting OEM Directory", "Querying partner database...");
    
    let percent = 0;
    const interval = setInterval(() => {
        percent += 10;
        if (percent <= 30) {
            updateProgressBar(percent, "Extracting solution catalogs...");
        } else if (percent <= 65) {
            updateProgressBar(percent, "Formatting CSV output data...");
        } else if (percent < 95) {
            updateProgressBar(percent, "Finalizing package payload...");
        } else {
            clearInterval(interval);
            updateProgressBar(100, "Initiating download...");
            setTimeout(() => {
                hideProgressOverlay();
                window.location.href = exportUrl;
            }, 600);
        }
    }, 90);
}

document.addEventListener('DOMContentLoaded', () => {
    const exportLinks = document.querySelectorAll('a[href$="/export/csv"]');
    exportLinks.forEach(link => {
        link.addEventListener('click', handleCSVExport);
    });
});

// ==========================================
// Deletion Security Math Puzzle Check
// ==========================================

function solveMathPuzzle(confirmText) {
    const num1 = Math.floor(Math.random() * 8) + 2; // 2-9
    const num2 = Math.floor(Math.random() * 8) + 2; // 2-9
    const sum = num1 + num2;
    
    const userInput = prompt(`⚠️ ${confirmText}\n\nSECURITY CHECK: To confirm deletion, solve this math puzzle:\n\nWhat is ${num1} + ${num2}?`);
    if (userInput === null) {
        return false;
    }
    
    if (parseInt(userInput.trim(), 10) !== sum) {
        alert("❌ Incorrect answer! Deletion aborted.");
        return false;
    }
    
    return true;
}

function confirmMathPuzzle(event) {
    const solved = solveMathPuzzle("Are you sure you want to proceed with this deletion?");
    if (!solved) {
        event.preventDefault();
        return false;
    }
    return true;
}

function showCustomModalDialog(htmlContent, onClose) {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.style.display = 'flex';
    backdrop.style.alignItems = 'center';
    backdrop.style.justifyContent = 'center';
    backdrop.style.zIndex = '99999';
    
    const content = document.createElement('div');
    content.className = 'modal-content';
    content.style.maxWidth = '500px';
    content.style.width = '90%';
    content.style.animation = 'fadeInUp 0.3s ease forwards';
    content.innerHTML = htmlContent;
    
    backdrop.appendChild(content);
    document.body.appendChild(backdrop);
    
    const btn = content.querySelector('#btn-close-import-summary');
    if (btn) {
        btn.addEventListener('click', () => {
            backdrop.remove();
            if (onClose) onClose();
        });
    }
}

// Expose functions globally for inline HTML execution
window.switchAddMode = switchAddMode;
window.handleQRScanFile = handleQRScanFile;
window.handleOCRScanFile = handleOCRScanFile;
window.showCustomModalDialog = showCustomModalDialog;
window.confirmMathPuzzle = confirmMathPuzzle;

// Toggle Accordion Group
function toggleCategoryAccordion(id, autoScroll = false) {
    const content = document.getElementById(id);
    if (!content) return;
    
    const group = content.parentElement;
    const isExpanded = group.classList.contains('expanded');
    
    if (isExpanded) {
        group.classList.remove('expanded');
        content.style.display = 'none';
    } else {
        group.classList.add('expanded');
        content.style.display = 'grid';
        if (autoScroll) {
            content.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
}

// Apply layout preferences on page load
function applyDashboardPreferences(prefs) {
    if (!prefs) return;
    const columns = prefs.columns || "2";
    const showStats = prefs.showStats !== false;
    const showReminders = prefs.showReminders !== false;
    
    const grid = document.querySelector('.dashboard-layout-grid');
    if (grid) {
        if (columns === "1") {
            grid.classList.add('layout-single-column');
        } else {
            grid.classList.remove('layout-single-column');
        }
    }
    
    const statsSec = document.querySelector('.stats-grid');
    if (statsSec) {
        statsSec.style.display = showStats ? 'grid' : 'none';
    }
    
    const remindersAside = document.querySelector('aside.glass-card');
    if (remindersAside) {
        remindersAside.style.display = showReminders ? 'block' : 'none';
    }
    
    // Sync settings inputs
    const selectTheme = document.getElementById('pref-theme');
    if (selectTheme && window.USER_THEME) {
        selectTheme.value = window.USER_THEME;
    }
    
    const radio1 = document.getElementById('cols-1');
    const radio2 = document.getElementById('cols-2');
    if (radio1 && radio2) {
        if (columns === "1") radio1.checked = true;
        else radio2.checked = true;
    }
    
    const checkStats = document.getElementById('show-stats');
    if (checkStats) checkStats.checked = showStats;
    
    const checkReminders = document.getElementById('show-reminders');
    if (checkReminders) checkReminders.checked = showReminders;
}

// Save layout preferences to database
function saveUserPreferences() {
    const selectTheme = document.getElementById('pref-theme');
    const theme = selectTheme ? selectTheme.value : 'theme-slate-dark';
    
    const radio1 = document.getElementById('cols-1');
    const columns = (radio1 && radio1.checked) ? "1" : "2";
    
    const checkStats = document.getElementById('show-stats');
    const showStats = checkStats ? checkStats.checked : true;
    
    const checkReminders = document.getElementById('show-reminders');
    const showReminders = checkReminders ? checkReminders.checked : true;
    
    const currPwdInput = document.getElementById('pref-curr-pwd');
    const newPwdInput = document.getElementById('pref-new-pwd');
    const confPwdInput = document.getElementById('pref-conf-pwd');
    
    const currPwd = currPwdInput ? currPwdInput.value.trim() : '';
    const newPwd = newPwdInput ? newPwdInput.value : '';
    const confPwd = confPwdInput ? confPwdInput.value : '';
    
    const data = {
        theme: theme,
        columns: columns,
        showStats: showStats,
        showReminders: showReminders
    };
    
    if (newPwd) {
        if (!currPwd) {
            alert("❌ Current password is required to change password.");
            return;
        }
        if (newPwd !== confPwd) {
            alert("❌ New passwords do not match.");
            return;
        }
        if (newPwd.length < 8) {
            alert("❌ Password must be at least 8 characters long.");
            return;
        }
        if (!/[A-Z]/.test(newPwd)) {
            alert("❌ Password must contain at least one uppercase letter.");
            return;
        }
        if (!/[a-z]/.test(newPwd)) {
            alert("❌ Password must contain at least one lowercase letter.");
            return;
        }
        if (!/\d/.test(newPwd)) {
            alert("❌ Password must contain at least one number.");
            return;
        }
        if (!/[!@#$%^&*(),.?":{}|<>]/.test(newPwd)) {
            alert("❌ Password must contain at least one special character.");
            return;
        }
        data.curr_password = currPwd;
        data.new_password = newPwd;
    }
    
    fetch(getAppUrl('/user/preferences'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(resJson => {
        if (resJson.status === 'success') {
            showToast("🎉 Preferences updated!");
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            alert("Error: " + resJson.message);
        }
    })
    .catch(err => {
        console.error("Preferences save error:", err);
        alert("Could not update portal settings.");
    });
}

// Trigger Sync & Clean backend task
function triggerWebRefresh(contactId) {
    const btn = document.getElementById('btn-sync-clean');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `⏳ Syncing & Cleaning...`;
    }
    
    showProgressOverlay("Sync & Clean Partner details", "Stripping junk characters and querying website solutions...");
    updateProgressBar(20, "Analyzing data encoding...");
    
    fetch(getAppUrl(`/contact/${contactId}/refresh-web`), {
        method: 'POST'
    })
    .then(res => res.json())
    .then(resJson => {
        updateProgressBar(70, "Persisting cleaned database records...");
        setTimeout(() => {
            updateProgressBar(100, "Refreshed!");
            setTimeout(() => {
                hideProgressOverlay();
                if (resJson.status === 'success') {
                    alert("✅ Sync Completed:\n\n" + resJson.message);
                    window.location.reload();
                } else {
                    alert("❌ Sync Failed:\n\n" + resJson.message);
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = `🔄 Sync & Clean`;
                    }
                }
            }, 300);
        }, 400);
    })
    .catch(err => {
        console.error("Sync error:", err);
        hideProgressOverlay();
        alert("❌ Connection error. Sync failed.");
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `🔄 Sync & Clean`;
        }
    });
}

// Page Loader screen handler
function hidePageLoader() {
    const loader = document.getElementById('page-loader');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => {
            loader.style.visibility = 'hidden';
            loader.style.display = 'none';
        }, 400);
    }
}

if (document.readyState === 'complete') {
    hidePageLoader();
} else {
    window.addEventListener('load', hidePageLoader);
}

// Setup settings on page load
document.addEventListener('DOMContentLoaded', () => {
    if (window.USER_PREFERENCES) {
        applyDashboardPreferences(window.USER_PREFERENCES);
    }
    
    // Auto-open preferences modal if URL query specifies it
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('preferences') === '1') {
        openModal('preferences-modal');
    }
});

// Expose additional functions globally
window.toggleCategoryAccordion = toggleCategoryAccordion;
window.saveUserPreferences = saveUserPreferences;
window.triggerWebRefresh = triggerWebRefresh;

// Expand/Collapse all categories globally
function expandAllCategories() {
    const groups = document.querySelectorAll('.category-group');
    groups.forEach(group => {
        const content = group.querySelector('.category-content');
        if (content) {
            group.classList.add('expanded');
            content.style.display = 'grid';
        }
    });
}

function collapseAllCategories() {
    const groups = document.querySelectorAll('.category-group');
    groups.forEach(group => {
        const content = group.querySelector('.category-content');
        if (content) {
            group.classList.remove('expanded');
            content.style.display = 'none';
        }
    });
}

window.expandAllCategories = expandAllCategories;
window.collapseAllCategories = collapseAllCategories;

// Extract domain name from URL helper
function getDomainFromUrl(url) {
    if (!url) return '';
    let cleaned = url.trim().toLowerCase();
    if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://')) {
        cleaned = 'https://' + cleaned;
    }
    try {
        const parsed = new URL(cleaned);
        let domain = parsed.hostname;
        if (domain.startsWith('www.')) {
            domain = domain.substring(4);
        }
        return domain;
    } catch (e) {
        // Fallback for simple domain strings
        return cleaned.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0];
    }
}

// Bind logo auto-fetching preview event listeners
document.addEventListener('DOMContentLoaded', () => {
    const websiteInput = document.getElementById('website');
    if (websiteInput) {
        // Auto-fetch logo preview on input change/blur
        websiteInput.addEventListener('blur', () => {
            const val = websiteInput.value.trim();
            const domain = getDomainFromUrl(val);
            const logoContainer = document.getElementById('company-logo-container');
            if (domain && logoContainer) {
                logoContainer.innerHTML = `<img src="https://logo.clearbit.com/${domain}" alt="Logo" style="width: 100%; height: 100%; object-fit: contain; background: white;" onerror="this.parentElement.innerHTML='🌐';">`;
            }
        });
    }

    const editWebsiteInput = document.getElementById('edit_website');
    if (editWebsiteInput) {
        editWebsiteInput.addEventListener('blur', () => {
            const val = editWebsiteInput.value.trim();
            const domain = getDomainFromUrl(val);
            const previewContainer = document.getElementById('edit-company-logo-preview');
            const mainLogoContainer = document.getElementById('company-logo-container');
            if (domain) {
                const imgHtml = `<img src="https://logo.clearbit.com/${domain}" alt="Logo" style="width: 100%; height: 100%; object-fit: contain; background: white;" onerror="this.parentElement.innerHTML='🌐';">`;
                if (previewContainer) previewContainer.innerHTML = imgHtml;
                if (mainLogoContainer) {
                    mainLogoContainer.innerHTML = `<img src="https://logo.clearbit.com/${domain}" alt="Logo" style="width: 48px; height: 48px; border-radius: 12px; object-fit: contain; background: rgba(255,255,255,0.04); border: 1px solid var(--border-glass);" onerror="this.parentElement.innerHTML='🌐';">`;
                }
            }
        });
    }
});

// Dropdown More Actions menu helper functions
function toggleActionsDropdown(event) {
    event.stopPropagation();
    const menu = document.getElementById('actions-dropdown-menu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
    }
}

function closeActionsDropdown() {
    const menu = document.getElementById('actions-dropdown-menu');
    if (menu) menu.style.display = 'none';
}

// Bind dropdown outside click handler
window.addEventListener('click', () => {
    closeActionsDropdown();
});

window.toggleActionsDropdown = toggleActionsDropdown;
window.closeActionsDropdown = closeActionsDropdown;

// Global Searchable Autocomplete Select Dropdown Widget
function initSearchableSelects() {
    const selects = document.querySelectorAll('select:not(.no-searchable-select)');
    console.log("Initializing searchable autocomplete selects for " + selects.length + " dropdowns.");
    
    selects.forEach(select => {
        if (select.dataset.searchableSelectInit) return;
        if (!select.parentNode) return;
        select.dataset.searchableSelectInit = 'true';
        
        // Hide native select
        select.style.display = 'none';
        
        // Create wrapper container
        const wrapper = document.createElement('div');
        wrapper.className = 'searchable-select-wrapper';
        wrapper.style.position = 'relative';
        wrapper.style.width = select.style.width || '100%';
        wrapper.style.display = 'inline-block';
        
        // Create search input textbox
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control searchable-select-input';
        input.style.cursor = 'pointer';
        input.style.width = '100%';
        input.style.background = 'rgba(15, 23, 42, 0.6)';
        input.style.border = '1px solid rgba(255, 255, 255, 0.08)';
        input.style.color = 'white';
        input.style.paddingRight = '2.5rem';
        input.style.borderRadius = '8px';
        input.style.boxSizing = 'border-box';
        
        // Read native select attributes to replicate placeholder/styling
        const placeholderText = select.options[0] ? select.options[0].text : 'Select...';
        input.placeholder = placeholderText;
        
        // Set initial value based on selected option
        const selectedOpt = select.options[select.selectedIndex];
        if (selectedOpt && select.value !== "") {
            input.value = selectedOpt.text;
        }
        
        // Create dropdown menu list container
        const menu = document.createElement('div');
        menu.className = 'searchable-select-menu';
        menu.style.display = 'none';
        menu.style.position = 'absolute';
        menu.style.top = '100%';
        menu.style.left = '0';
        menu.style.right = '0';
        menu.style.background = '#1e293b';
        menu.style.border = '1px solid rgba(255, 255, 255, 0.1)';
        menu.style.borderRadius = '8px';
        menu.style.zIndex = '9999';
        menu.style.maxHeight = '200px';
        menu.style.overflowY = 'auto';
        menu.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.5)';
        menu.style.marginTop = '4px';
        
        wrapper.appendChild(input);
        wrapper.appendChild(menu);
        
        // Insert wrapper in place of original select
        select.parentNode.insertBefore(wrapper, select);
        
        // Function to rebuild options list inside the menu
        function rebuildOptions(filterText = '') {
            menu.innerHTML = '';
            const normalizedFilter = filterText.toLowerCase();
            let matchesCount = 0;
            
            for (let idx = 0; idx < select.options.length; idx++) {
                const opt = select.options[idx];
                if (idx === 0 && opt.value === "" && select.options.length > 1) {
                    continue;
                }
                
                const optText = opt.text;
                if (optText.toLowerCase().includes(normalizedFilter)) {
                    const item = document.createElement('div');
                    item.className = 'searchable-select-item';
                    item.style.padding = '0.5rem 0.75rem';
                    item.style.color = 'white';
                    item.style.cursor = 'pointer';
                    item.style.fontSize = '0.85rem';
                    item.style.transition = 'background 0.2s ease';
                    item.style.textAlign = 'left';
                    
                    if (select.value === opt.value) {
                        item.classList.add('selected');
                        item.style.background = '#3b82f6';
                    }
                    
                    item.innerText = optText;
                    item.dataset.value = opt.value;
                    item.dataset.index = idx;
                    
                    item.addEventListener('mouseenter', () => {
                        if (select.value !== opt.value) {
                            item.style.background = 'rgba(255, 255, 255, 0.08)';
                            item.style.color = '#3b82f6';
                        }
                    });
                    item.addEventListener('mouseleave', () => {
                        if (select.value !== opt.value) {
                            item.style.background = 'transparent';
                            item.style.color = 'white';
                        } else {
                            item.style.background = '#3b82f6';
                            item.style.color = 'white';
                        }
                    });
                    
                    item.addEventListener('click', (e) => {
                        e.stopPropagation();
                        select.selectedIndex = idx;
                        input.value = optText;
                        menu.style.display = 'none';
                        const event = new Event('change', { bubbles: true });
                        select.dispatchEvent(event);
                    });
                    
                    menu.appendChild(item);
                    matchesCount++;
                }
            }
            
            if (matchesCount === 0) {
                const noResults = document.createElement('div');
                noResults.className = 'searchable-select-no-results';
                noResults.style.padding = '0.5rem 0.75rem';
                noResults.style.color = 'var(--text-muted)';
                noResults.style.fontSize = '0.85rem';
                noResults.style.fontStyle = 'italic';
                noResults.style.textAlign = 'center';
                noResults.innerText = 'No matching options found';
                menu.appendChild(noResults);
            }
        }
        
        let highlightedIdx = -1;
        
        function getVisibleItems() {
            return menu.querySelectorAll('.searchable-select-item');
        }
        
        function updateHighlight(items, direction) {
            items.forEach((item) => {
                const isSelected = item.classList.contains('selected');
                if (isSelected) {
                    item.style.background = '#3b82f6';
                    item.style.color = 'white';
                } else {
                    item.style.background = 'transparent';
                    item.style.color = 'white';
                }
                item.classList.remove('highlighted');
            });
            
            if (direction === 'down') {
                highlightedIdx = (highlightedIdx + 1) % items.length;
            } else if (direction === 'up') {
                highlightedIdx = (highlightedIdx - 1 + items.length) % items.length;
            }
            
            const target = items[highlightedIdx];
            if (target) {
                target.classList.add('highlighted');
                target.style.background = 'rgba(255, 255, 255, 0.15)';
                target.style.color = '#3b82f6';
                target.scrollIntoView({ block: 'nearest' });
            }
        }
        
        // Open/close dropdown logic
        input.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.searchable-select-menu').forEach(m => {
                if (m !== menu) m.style.display = 'none';
            });
            
            const isOpen = menu.style.display === 'block';
            menu.style.display = isOpen ? 'none' : 'block';
            if (!isOpen) {
                input.value = '';
                highlightedIdx = -1;
                rebuildOptions('');
                input.focus();
            } else {
                const opt = select.options[select.selectedIndex];
                if (opt && select.value !== "") {
                    input.value = opt.text;
                }
            }
        });
        
        input.addEventListener('input', () => {
            menu.style.display = 'block';
            highlightedIdx = -1;
            rebuildOptions(input.value);
        });

        // Keyboard Navigation handler
        input.addEventListener('keydown', (e) => {
            const items = getVisibleItems();
            if (items.length === 0) return;
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (menu.style.display !== 'block') {
                    menu.style.display = 'block';
                    highlightedIdx = -1;
                    rebuildOptions(input.value);
                }
                updateHighlight(items, 'down');
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                updateHighlight(items, 'up');
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const activeItem = menu.querySelector('.searchable-select-item.highlighted');
                if (activeItem) {
                    activeItem.click();
                } else if (items[0]) {
                    items[0].click();
                }
            } else if (e.key === 'Escape') {
                menu.style.display = 'none';
                const opt = select.options[select.selectedIndex];
                if (opt && select.value !== "") {
                    input.value = opt.text;
                }
            }
        });
        
        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) {
                menu.style.display = 'none';
                const opt = select.options[select.selectedIndex];
                if (opt && select.value !== "") {
                    input.value = opt.text;
                } else {
                    input.value = '';
                }
            }
        });
    });
}

// Bind export actions to animated progress bars
function initExportInterceptors() {
    const exportSelectors = [
        'a[href*="/export-boq-csv"]',
        'a[href*="/export-checklist-csv"]',
        'a[href$="/export/csv"]',
        'a[href$="/admin/backup"]',
        'a[href*="/export-checklist-template"]'
    ];
    
    document.querySelectorAll(exportSelectors.join(',')).forEach(link => {
        if (link.dataset.exportIntercepted) return;
        link.dataset.exportIntercepted = 'true';
        
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            
            let title = "Exporting Data";
            let startMsg = "Connecting to SQLite database...";
            let step1 = "Querying data records...";
            let step2 = "Structuring table fields...";
            let step3 = "Compiling binary download stream...";
            
            if (href.includes('export-boq-csv')) {
                title = "Exporting BoQ Matrix";
                step1 = "Selecting parsed specification items...";
                step2 = "Aggregating associated OEMs and submission checkboxes...";
            } else if (href.includes('export-checklist-csv')) {
                title = "Exporting Tender Checklist";
                step1 = "Retrieving checklist documents & remarks...";
                step2 = "Formatting verification flags...";
            } else if (href.includes('admin/backup')) {
                title = "Creating Portal Backup";
                startMsg = "Packaging files...";
                step1 = "Creating SQLite database dump...";
                step2 = "Compressing attachment uploads directory...";
                step3 = "Building final secure backup ZIP archive...";
            }
            
            showProgressOverlay(title, startMsg);
            
            setTimeout(() => {
                updateProgressBar(30, step1);
                setTimeout(() => {
                    updateProgressBar(70, step2);
                    setTimeout(() => {
                        updateProgressBar(90, step3);
                        setTimeout(() => {
                            updateProgressBar(100, "Download initiated!");
                            setTimeout(() => {
                                hideProgressOverlay();
                                window.location.href = href;
                            }, 500);
                        }, 500);
                    }, 400);
                }, 400);
            }, 300);
        });
    });
}

// Auto-run or bind on DOMContentLoaded
if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => {
        initSearchableSelects();
        initExportInterceptors();
        initAllSorting();
    });
} else {
    initSearchableSelects();
    initExportInterceptors();
    initAllSorting();
}

function initAllSorting() {
    if (document.getElementById('rfps-table-body')) {
        initDragAndDropSort('rfps-table-body', 'rfps_list_order');
    }
    if (document.getElementById('checklist-table-body')) {
        const rfpId = window.RFP_ID || 'general';
        initDragAndDropSort('checklist-table-body', `rfp_checklist_order_${rfpId}`);
    }
}

function initDragAndDropSort(tbodyId, storageKey) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    
    let rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length === 0) return;
    
    // Sort logic
    const savedOrderStr = localStorage.getItem(storageKey);
    if (savedOrderStr) {
        try {
            const savedOrder = JSON.parse(savedOrderStr);
            rows.sort((a, b) => {
                const idA = a.getAttribute('data-id');
                const idB = b.getAttribute('data-id');
                const idxA = savedOrder.indexOf(idA);
                const idxB = savedOrder.indexOf(idB);
                if (idxA === -1 && idxB === -1) return 0;
                if (idxA === -1) return 1;
                if (idxB === -1) return -1;
                return idxA - idxB;
            });
        } catch (e) {
            console.error("Error parsing saved order for " + storageKey, e);
        }
    } else {
        // Default: Sort alphabetically (A to Z) by data-name, or fall back to innerText
        rows.sort((a, b) => {
            const attrA = a.getAttribute('data-name');
            const attrB = b.getAttribute('data-name');
            
            let nameA = attrA ? attrA.trim() : '';
            let nameB = attrB ? attrB.trim() : '';
            
            if (!nameA) {
                const divA = a.querySelector('td div');
                nameA = divA ? divA.textContent.trim() : '';
            }
            if (!nameB) {
                const divB = b.querySelector('td div');
                nameB = divB ? divB.textContent.trim() : '';
            }
            
            return nameA.toLowerCase().localeCompare(nameB.toLowerCase());
        });
    }
    
    // Append rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
    
    // Wire drag & drop
    rows.forEach(row => {
        row.setAttribute('draggable', 'true');
        row.style.cursor = 'grab';
        
        row.addEventListener('dragstart', handleDragStart);
        row.addEventListener('dragover', handleDragOver);
        row.addEventListener('dragleave', handleDragLeave);
        row.addEventListener('drop', handleDrop);
        row.addEventListener('dragend', handleDragEnd);
    });
    
    let dragSrcEl = null;
    
    function handleDragStart(e) {
        dragSrcEl = this;
        this.style.opacity = '0.4';
        this.style.border = '2px dashed var(--primary)';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.outerHTML);
    }
    
    function handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault(); 
        }
        e.dataTransfer.dropEffect = 'move';
        this.classList.add('drag-over');
        this.style.background = 'rgba(99, 102, 241, 0.15)';
        return false;
    }
    
    function handleDragLeave(e) {
        this.classList.remove('drag-over');
        this.style.background = '';
    }
    
    function handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }
        
        if (dragSrcEl !== this) {
            const allRows = Array.from(tbody.querySelectorAll('tr'));
            const dragIdx = allRows.indexOf(dragSrcEl);
            const dropIdx = allRows.indexOf(this);
            
            if (dragIdx < dropIdx) {
                this.parentNode.insertBefore(dragSrcEl, this.nextSibling);
            } else {
                this.parentNode.insertBefore(dragSrcEl, this);
            }
            
            // Save new order to localStorage
            const newOrder = Array.from(tbody.querySelectorAll('tr')).map(r => r.getAttribute('data-id'));
            localStorage.setItem(storageKey, JSON.stringify(newOrder));
        }
        return false;
    }
    
    function handleDragEnd(e) {
        this.style.opacity = '1';
        this.style.border = '';
        const allRows = tbody.querySelectorAll('tr');
        allRows.forEach(r => {
            r.classList.remove('drag-over');
            r.style.background = '';
            r.style.opacity = '1';
            r.style.border = '';
        });
    }
}

function toggleTableSort(tbodyId, keySelector, button) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    
    let rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length === 0) return;
    
    let currentDir = button.getAttribute('data-dir') || '';
    let newDir = 'asc';
    
    if (currentDir === 'asc') {
        newDir = 'desc';
    } else {
        newDir = 'asc';
    }
    
    button.setAttribute('data-dir', newDir);
    
    const iconSpan = button.querySelector('.sort-icon');
    if (iconSpan) {
        iconSpan.textContent = newDir === 'asc' ? '▲ A-Z' : '▼ Z-A';
    }
    
    rows.sort((a, b) => {
        let valA = '';
        let valB = '';
        
        const elA = a.querySelector(keySelector);
        const elB = b.querySelector(keySelector);
        
        if (elA) {
            if (elA.tagName === 'INPUT' || elA.tagName === 'SELECT' || elA.tagName === 'TEXTAREA') {
                valA = elA.value || elA.getAttribute('value') || '';
            } else {
                valA = elA.textContent || '';
            }
        }
        
        if (elB) {
            if (elB.tagName === 'INPUT' || elB.tagName === 'SELECT' || elB.tagName === 'TEXTAREA') {
                valB = elB.value || elB.getAttribute('value') || '';
            } else {
                valB = elB.textContent || '';
            }
        }
        
        valA = valA.trim().toLowerCase();
        valB = valB.trim().toLowerCase();
        
        if (newDir === 'asc') {
            return valA.localeCompare(valB);
        } else {
            return valB.localeCompare(valA);
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
    
    let storageKey = '';
    if (tbodyId === 'rfps-table-body') {
        storageKey = 'rfps_list_order';
    } else if (tbodyId === 'checklist-table-body') {
        const rfpId = window.RFP_ID || 'general';
        storageKey = `rfp_checklist_order_${rfpId}`;
    }
    
    if (storageKey) {
        const newOrder = rows.map(r => r.getAttribute('data-id'));
        localStorage.setItem(storageKey, JSON.stringify(newOrder));
    }
}

window.initSearchableSelects = initSearchableSelects;
window.initExportInterceptors = initExportInterceptors;
window.initDragAndDropSort = initDragAndDropSort;
window.initAllSorting = initAllSorting;
window.toggleTableSort = toggleTableSort;

// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(reg => console.log('Service Worker registered successfully:', reg.scope))
            .catch(err => console.error('Service Worker registration failed:', err));
    });
}

// Inject Manifest & PWA Meta tags into <head> dynamically
(function injectPWAMeta() {
    const head = document.head;
    if (!head) return;
    
    // Manifest Link
    if (!document.querySelector('link[rel="manifest"]')) {
        const link = document.createElement('link');
        link.rel = 'manifest';
        link.href = '/manifest.json';
        head.appendChild(link);
    }
    
    // Apple Web App Capable Meta
    if (!document.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
        const meta = document.createElement('meta');
        meta.name = 'apple-mobile-web-app-capable';
        meta.content = 'yes';
        head.appendChild(meta);
    }
    
    // Apple Status Bar Style Meta
    if (!document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]')) {
        const meta = document.createElement('meta');
        meta.name = 'apple-mobile-web-app-status-bar-style';
        meta.content = 'black-translucent';
        head.appendChild(meta);
    }
    
    // Theme Color Meta
    if (!document.querySelector('meta[name="theme-color"]')) {
        const meta = document.createElement('meta');
        meta.name = 'theme-color';
        meta.content = '#6366f1';
        head.appendChild(meta);
    }
})();

// Inject Mobile bottom nav & top header & responsive table tags
(function injectMobileLayout() {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('pwa-mobile-bottom-nav')) return;
        
        // 1. Mobile Bottom Navigation
        const bottomNav = document.createElement('div');
        bottomNav.id = 'pwa-mobile-bottom-nav';
        bottomNav.className = 'mobile-bottom-nav';
        
        const path = window.location.pathname;
        const isDashboard = path === '/' || path.includes('/dashboard') || path === '/dashboard.html';
        const isNews = path.includes('/news');
        const isRfps = path.includes('/rfps');
        const isAdmin = path.includes('/admin');
        
        bottomNav.innerHTML = `
            <a href="/" class="mobile-nav-item ${isDashboard ? 'active' : ''}">
                <span class="icon">📊</span>
                <span class="label">Dashboard</span>
            </a>
            <a href="/news" class="mobile-nav-item ${isNews ? 'active' : ''}">
                <span class="icon">📰</span>
                <span class="label">OEM News</span>
            </a>
            <a href="/rfps" class="mobile-nav-item ${isRfps ? 'active' : ''}">
                <span class="icon">📋</span>
                <span class="label">RFPs</span>
            </a>
            <a href="/admin" class="mobile-nav-item ${isAdmin ? 'active' : ''}">
                <span class="icon">🛡️</span>
                <span class="label">Admin</span>
            </a>
        `;
        document.body.appendChild(bottomNav);
        
        // 2. Mobile Top Header
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            const topHeader = document.createElement('div');
            topHeader.id = 'pwa-mobile-top-header';
            topHeader.className = 'mobile-top-header';
            topHeader.innerHTML = `
                <div class="logo">
                    <span>📂</span> OEM Portal
                </div>
                <div class="user-action" onclick="openModal('preferences-modal')">
                    ⚙️
                </div>
            `;
            mainContent.insertBefore(topHeader, mainContent.firstChild);
        }
        
        // 3. Auto data-labels for table mobile card layouts
        document.querySelectorAll('table').forEach(table => {
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            if (headers.length === 0) return;
            
            table.querySelectorAll('tbody tr').forEach(row => {
                row.querySelectorAll('td').forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        });
    });
})();

function copyToClipboard(text, btn) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '✓';
        btn.style.color = '#34d399';
        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.style.color = '';
        }, 1500);
    }).catch(err => {
        console.error('Failed to copy text:', err);
    });
}
window.copyToClipboard = copyToClipboard;


