document.addEventListener('DOMContentLoaded', function() {
    const rawData = JSON.parse(document.getElementById('chart-data').textContent);
    
    // Total sum calculations for Doughnut chart
    const totalHomepage = rawData.homepage.reduce((a, b) => a + b, 0);
    const totalProject = rawData.project.reduce((a, b) => a + b, 0);
    const totalBlog = rawData.blog.reduce((a, b) => a + b, 0);
    
    // Render Doughnut chart
    const ctxDoughnut = document.getElementById('viewsDistributionChart').getContext('2d');
    const distributionChart = new Chart(ctxDoughnut, {
        type: 'doughnut',
        data: {
            labels: ['Homepage', 'Projects', 'Blogs'],
            datasets: [{
                data: [totalHomepage, totalProject, totalBlog],
                backgroundColor: [
                    '#3498db', // Blue
                    '#e67e22', // Orange
                    '#2ecc71'  // Green
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 15,
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            const total = totalHomepage + totalProject + totalBlog;
                            const percentage = total > 0 ? Math.round((val / total) * 100) : 0;
                            return ` ${context.label}: ${val} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });

    // Prepare line chart configurations
    const ctxLine = document.getElementById('viewsTimelineChart').getContext('2d');
    
    // Create gradients for line datasets
    const createGradient = (colorStart, colorEnd) => {
        const gradient = ctxLine.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        return gradient;
    };

    const colors = {
        total: { stroke: '#9b59b6', fill: createGradient('rgba(155, 89, 182, 0.2)', 'rgba(155, 89, 182, 0.0)') },
        homepage: { stroke: '#3498db', fill: createGradient('rgba(52, 152, 219, 0.15)', 'rgba(52, 152, 219, 0.0)') },
        project: { stroke: '#e67e22', fill: createGradient('rgba(230, 126, 34, 0.15)', 'rgba(230, 126, 34, 0.0)') },
        blog: { stroke: '#2ecc71', fill: createGradient('rgba(46, 204, 113, 0.15)', 'rgba(46, 204, 113, 0.0)') }
    };

    // Chart init configuration
    let timelineChart = new Chart(ctxLine, {
        type: 'line',
        data: {
            labels: rawData.dates,
            datasets: [
                {
                    label: 'Total Views',
                    data: rawData.total,
                    borderColor: colors.total.stroke,
                    backgroundColor: colors.total.fill,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointRadius: 2,
                    pointHoverRadius: 6,
                },
                {
                    label: 'Homepage',
                    data: rawData.homepage,
                    borderColor: colors.homepage.stroke,
                    backgroundColor: colors.homepage.fill,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 1,
                    pointHoverRadius: 4,
                    hidden: true
                },
                {
                    label: 'Projects',
                    data: rawData.project,
                    borderColor: colors.project.stroke,
                    backgroundColor: colors.project.fill,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 1,
                    pointHoverRadius: 4,
                    hidden: true
                },
                {
                    label: 'Blogs',
                    data: rawData.blog,
                    borderColor: colors.blog.stroke,
                    backgroundColor: colors.blog.fill,
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 1,
                    pointHoverRadius: 4,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 15,
                        padding: 10,
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                            size: 11
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 8,
                        font: { size: 10 }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(200, 200, 200, 0.1)'
                    },
                    ticks: {
                        precision: 0,
                        font: { size: 10 }
                    }
                }
            }
        }
    });

    // Handle Time range dropdown filtering (slicing dates & data client-side)
    const timeRangeSelect = document.getElementById('timeRangeSelect');
    
    function updateChartTimeframe() {
        const days = parseInt(timeRangeSelect.value);
        const totalLength = rawData.dates.length;
        const startIndex = Math.max(0, totalLength - days);
        
        // Slice labels
        timelineChart.data.labels = rawData.dates.slice(startIndex);
        
        // Slice datasets
        timelineChart.data.datasets[0].data = rawData.total.slice(startIndex);
        timelineChart.data.datasets[1].data = rawData.homepage.slice(startIndex);
        timelineChart.data.datasets[2].data = rawData.project.slice(startIndex);
        timelineChart.data.datasets[3].data = rawData.blog.slice(startIndex);
        
        timelineChart.update();
    }
    
    timeRangeSelect.addEventListener('change', updateChartTimeframe);
    
    // Custom Dropdown Functionality
    const dropdown = document.getElementById('timeRangeDropdown');
    const selected = document.getElementById('timeRangeSelected');
    const optionsList = document.getElementById('timeRangeOptions');
    const options = optionsList.querySelectorAll('li');

    selected.addEventListener('click', function(e) {
        dropdown.classList.toggle('open');
        e.stopPropagation();
    });

    options.forEach(option => {
        option.addEventListener('click', function(e) {
            selected.innerHTML = this.textContent + ' <i class="fas fa-chevron-down" style="font-size: 0.8rem; color: #7f8c8d;"></i>';
            options.forEach(opt => opt.classList.remove('active'));
            this.classList.add('active');
            
            timeRangeSelect.value = this.dataset.value;
            timeRangeSelect.dispatchEvent(new Event('change'));
            
            dropdown.classList.remove('open');
            e.stopPropagation();
        });
    });

    document.addEventListener('click', function(e) {
        if (!dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });

    // Initial triggering
    updateChartTimeframe();
});
