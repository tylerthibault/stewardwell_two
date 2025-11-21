

document.addEventListener('DOMContentLoaded', function () {
    all_tabs = document.querySelectorAll('.my-tabs .my-tab-link');
    all_panes = document.querySelectorAll('.my-tab-pane');
    
    console.log('Tabs found:', all_tabs);
    console.log('Panes found:', all_panes);

    // Desktop tab click handlers
    all_tabs.forEach(function (tab) {
        tab.addEventListener('click', function (e) {
            e.preventDefault();
            const target_id = tab.getAttribute('data-my-target');
            const target_pane = document.querySelector(target_id);
            console.log('Tab clicked:', tab, 'Target pane:', target_pane);
            showTab(tab, target_pane);
        });
    });

    // Mobile dropdown handler
    const dropdown = document.querySelector('.my-tabs-dropdown select');
    if (dropdown) {
        dropdown.addEventListener('change', function (e) {
            const target_id = e.target.value;
            const target_pane = document.querySelector(target_id);
            const target_tab = document.querySelector(`.my-tab-link[data-my-target="${target_id}"]`);
            console.log('Dropdown changed:', target_id, 'Target pane:', target_pane);
            if (target_pane && target_tab) {
                showTab(target_tab, target_pane);
            }
        });
    }

    function showTab(tab, pane) {
        // Hide all panes and remove active class from all tabs
        hideAllTabs();

        // activate the tab
        tab.classList.add('active');
        // activate the pane
        pane.classList.add('active');
    }

    function hideAllTabs() {
        all_tabs.forEach(function (t) {
            t.classList.remove('active');
        });
        all_panes.forEach(function (p) {
            p.classList.remove('active');
        });
    }
});