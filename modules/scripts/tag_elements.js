(function() {
    // Remove existing tags
    const existingTags = document.querySelectorAll('.commuter-som-tag');
    existingTags.forEach(tag => tag.remove());

    const interactiveSelectors = [
        'button', 'input', 'select', 'textarea', 'a', 
        '[role="button"]', '[role="link"]', '[role="checkbox"]', '[role="radio"]'
    ];
    
    const elements = document.querySelectorAll(interactiveSelectors.join(','));
    let count = 0;

    elements.forEach(el => {
        // Simple visibility check
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0 || window.getComputedStyle(el).display === 'none' || window.getComputedStyle(el).visibility === 'hidden') {
            return;
        }

        count++;
        const tagId = count;
        el.setAttribute('data-som-id', tagId);

        // Create overlay tag
        const tag = document.createElement('div');
        tag.className = 'commuter-som-tag';
        tag.innerText = tagId;
        tag.style.position = 'absolute';
        tag.style.left = (window.scrollX + rect.left) + 'px';
        tag.style.top = (window.scrollY + rect.top) + 'px';
        tag.style.backgroundColor = 'red';
        tag.style.color = 'white';
        tag.style.fontSize = '12px';
        tag.style.fontWeight = 'bold';
        tag.style.padding = '2px 4px';
        tag.style.borderRadius = '3px';
        tag.style.zIndex = '1000000';
        tag.style.pointerEvents = 'none';
        
        document.body.appendChild(tag);
    });

    console.log(`[SoM] Tagged ${count} interactive elements.`);
})();
