(function () {
  // Configuration
  const config = {
    colors: {
      primary: {
        50: '#f0f9ff',
        100: '#e0f2fe',
        200: '#bae6fd',
        300: '#7dd3fc',
        400: '#38bdf8',
        500: '#0ea5e9',
        600: '#0284c7',
        700: '#0369a1',
        800: '#075985',
        900: '#0c4a6e',
      },
      gray: {
        50: '#f9fafb',
        100: '#f3f4f6',
        200: '#e5e7eb',
        300: '#d1d5db',
        400: '#9ca3af',
        500: '#6b7280',
        600: '#4b5563',
        700: '#374151',
        800: '#1f2937',
        900: '#111827',
      }
    },
    defaultDateRange: 30 // days
  };

  // State management
  const state = {
    currentPage: 1,
    chartPeriod: 'monthly',
    dateRangePicker: null,
    salesChart: null,
    sellers: []
  };

  // DOM Elements
  const elements = {
    loader: document.getElementById('loader'),
    sellerFilter: document.getElementById('seller-filter'),
    sellerSuggestions: document.getElementById('seller-suggestions'),
    dateRangeInput: document.getElementById('date-range'),
    chartButtons: {
      monthly: document.getElementById('chart-monthly'),
      weekly: document.getElementById('chart-weekly'),
      daily: document.getElementById('chart-daily')
    },
    pagination: {
      prev: document.getElementById('prev-page'),
      next: document.getElementById('next-page'),
      info: document.getElementById('pagination-info')
    }
  };

  // Utility Functions
  const utils = {
    showLoader: () => elements.loader.classList.remove('hidden'),
    hideLoader: () => elements.loader.classList.add('hidden'),

    showError: (message) => {
      Toastify({
        text: message,
        duration: 3000,
        close: true,
        gravity: "top",
        position: "right",
        style: {
          background: "#ef4444",
        },
        stopOnFocus: true,
      }).showToast();
    },

    fetchData: async (url) => {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status} for URL: ${url}`);
        }
        const data = await response.json();
        if (data.status !== 'success') {
          throw new Error(data.message || `API request failed for URL: ${url}`);
        }
        return data;
      } catch (error) {
        utils.showError(error.message);
        throw error;
      }
    },

    formatCurrency: (amount) => {
      return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
      }).format(amount);
    },

    formatChange: (value, isPercentage = false) => {
      const prefix = value >= 0 ? '+' : '';
      const color = value >= 0 ? 'text-green-600' : 'text-red-600';
      const icon = value >= 0
        ? `<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>`
        : `<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>`;

      const formattedValue = isPercentage
        ? `${prefix}${value.toFixed(1)}%`
        : `₹${Math.abs(value).toLocaleString('en-IN')}`;

      return `<span class="${color} flex items-center">${icon}${formattedValue} from last period</span>`;
    },

    getStatusBadge: (status) => {
      const statusMap = {
        'completed': { class: 'bg-green-100 text-green-800', text: 'Completed' },
        'processing': { class: 'bg-yellow-100 text-yellow-800', text: 'Processing' },
        'cancelled': { class: 'bg-red-100 text-red-800', text: 'Cancelled' },
        'default': { class: 'bg-gray-100 text-gray-800', text: 'Pending' }
      };

      return statusMap[status] || statusMap.default;
    }
  };

  // Data Fetching Functions
  const dataFetchers = {
    loadOverview: async (params = '') => {
      try {
        const { data } = await utils.fetchData(`/api/sales/overview${params}`);

        document.getElementById('total-sales').textContent = utils.formatCurrency(data.total_sales);
        document.getElementById('total-sales-change').innerHTML = utils.formatChange(data.total_sales_change, true);
        document.getElementById('order-count').textContent = data.order_count.toLocaleString('en-IN');
        document.getElementById('order-count-change').innerHTML = utils.formatChange(data.order_count_change, true);
        document.getElementById('avg-order-value').textContent = utils.formatCurrency(data.avg_order_value);
        document.getElementById('avg-order-change').innerHTML = utils.formatChange(data.avg_order_change, true);
      } catch (error) {
        console.error('Error loading overview:', error);
      }
    },

    loadSellers: async () => {
      if (!elements.sellerFilter) return;

      try {
        const { data } = await utils.fetchData('/api/sales/sellers');
        state.sellers = data;

        elements.sellerFilter.addEventListener('focus', () => {
          uiHelpers.showSellerSuggestions(state.sellers);
        });

        elements.sellerFilter.addEventListener('input', () => {
          const searchTerm = elements.sellerFilter.value.toLowerCase();
          const filteredSellers = state.sellers.filter(seller =>
            seller.name.toLowerCase().includes(searchTerm)
          );
          uiHelpers.showSellerSuggestions(filteredSellers);
        });

        document.addEventListener('click', (e) => {
          if (e.target !== elements.sellerFilter) {
            elements.sellerSuggestions.classList.add('hidden');
          }
        });
      } catch (error) {
        console.error('Error loading sellers:', error);
      }
    },

    loadSalesChart: async (params = '') => {
      try {
        const { data } = await utils.fetchData(`/api/sales/over-time${params}`);
        const salesCtx = document.getElementById('salesChart').getContext('2d');

        if (state.salesChart) {
          state.salesChart.destroy();
        }

        // Create gradient for line fill
        const gradient = salesCtx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, config.colors.primary[400]);
        gradient.addColorStop(1, config.colors.primary[50] + '80'); // Add transparency

        state.salesChart = new Chart(salesCtx, {
          type: 'line',
          data: {
            labels: data.labels,
            datasets: [{
              label: 'Sales (₹)',
              data: data.sales,
              borderColor: config.colors.primary[600],
              backgroundColor: gradient,
              fill: true,
              tension: 0.3,
              borderWidth: 3,
              pointBackgroundColor: config.colors.primary[600],
              pointBorderColor: config.colors.gray[50],
              pointBorderWidth: 2,
              pointRadius: 5,
              pointHoverRadius: 8,
              pointHitRadius: 10,
              pointStyle: 'circle'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  color: config.colors.primary[700],
                  font: {
                    family: "'Inter', sans-serif",
                    size: 14,
                    weight: 'bold'
                  }
                }
              },
              tooltip: {
                backgroundColor: config.colors.gray[800],
                titleColor: config.colors.gray[50],
                bodyColor: config.colors.gray[50],
                borderColor: config.colors.primary[600],
                borderWidth: 1,
                padding: 15,
                cornerRadius: 6,
                usePointStyle: true,
                callbacks: {
                  label: function (context) {
                    return `Sales: ${utils.formatCurrency(context.raw)}`;
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
                  color: config.colors.gray[500],
                  font: {
                    family: "'Inter', sans-serif",
                    size: 12
                  }
                }
              },
              y: {
                grid: {
                  color: config.colors.gray[200],
                  borderDash: [4, 4]
                },
                ticks: {
                  color: config.colors.gray[500],
                  font: {
                    family: "'Inter', sans-serif",
                    size: 12
                  },
                  callback: function (value) {
                    return '₹' + value.toLocaleString('en-IN');
                  }
                },
                beginAtZero: true
              }
            },
            animation: {
              duration: 1200,
              easing: 'easeInOutQuad'
            },
            elements: {
              line: {
                shadowColor: 'rgba(0,0,0,0.2)',
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowOffsetY: 4
              }
            }
          }
        });
      } catch (error) {
        console.error('Error loading sales chart:', error);
      }
    },

    loadTopProducts: async (params = '') => {
      try {
        const { data } = await utils.fetchData(`/api/sales/top-products${params}`);
        const container = document.getElementById('top-products');
        container.innerHTML = '';

        const icons = [
          { color: 'indigo', path: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
          { color: 'blue', path: 'M9 5l7 7-7 7' },
          { color: 'green', path: 'M13 10V3L4 14h7v7l9-11h-7z' },
          { color: 'purple', path: 'M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4' }
        ];

        data.forEach((product, index) => {
          const icon = icons[index % icons.length];
          const div = document.createElement('div');
          div.className = 'flex items-start';
          div.innerHTML = `
            <div class="bg-${icon.color}-100 p-2 rounded-lg mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-${icon.color}-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${icon.path}" />
              </svg>
            </div>
            <div class="flex-1">
              <h3 class="text-sm font-medium text-gray-900">${product.name}</h3>
              <p class="text-xs text-gray-500">${product.percentage.toFixed(1)}% of total sales</p>
              <div class="mt-1 w-full bg-gray-200 rounded-full h-1.5">
                <div class="bg-${icon.color}-600 h-1.5 rounded-full" style="width: ${product.percentage}%"></div>
              </div>
            </div>
            <span class="text-sm font-medium text-gray-900">${utils.formatCurrency(product.amount)}</span>
          `;
          container.appendChild(div);
        });
      } catch (error) {
        console.error('Error loading top products:', error);
        document.getElementById('top-products').innerHTML =
          '<p class="text-sm text-gray-500">Failed to load top products. Please try again.</p>';
      }
    },

    loadRecentSales: async (params = '', page = 1) => {
      try {
        const { data } = await utils.fetchData(`/api/sales/recent${params}&page=${page}`);
        const tbody = document.getElementById('recent-sales-body');
        tbody.innerHTML = '';

        if (data.orders.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="6" class="px-6 py-4 text-center text-sm text-gray-500">No transactions found</td>
            </tr>
          `;
          return;
        }

        data.orders.forEach(order => {
          const status = utils.getStatusBadge(order.status);
          const row = document.createElement('tr');
          row.className = 'hover:bg-gray-50 transition-colors duration-150';
          row.innerHTML = `
            <td class="px-3 py-3 md:px-6 md:py-4 text-sm border border-gray-200 text-center">${order.order_id}</td>
            <td class="px-3 py-3 md:px-6 md:py-4 text-sm border border-gray-200 text-center">${order.customer}</td>
            <td class="px-3 py-3 md:px-6 md:py-4 text-sm border border-gray-200 text-center">${order.product}</td>
            <td class="px-3 py-3 md:px-6 md:py-4 text-sm border border-gray-200 text-center">${utils.formatCurrency(order.amount)}</td>
            <td class="px-3 py-3 md:px-6 md:py-4 text-sm border border-gray-200 text-center">${new Date(order.date).toLocaleDateString('en-IN')}</td>
            <td class="px-3 py-3 md:px-6 md:py-4 text-sm border border-gray-200 text-center">
              <span class="py-2 px-4 inline-flex text-xs leading-5 font-semibold rounded-lg ${status.class}">${status.text}</span>
            </td>
          `;
          tbody.appendChild(row);
        });

        elements.pagination.info.innerHTML =
          `Showing <span class="font-medium">${(data.page - 1) * data.per_page + 1}</span> to 
          <span class="font-medium">${Math.min(data.page * data.per_page, data.total)}</span> of 
          <span class="font-medium">${data.total}</span> results`;

        elements.pagination.prev.disabled = data.page === 1;
        elements.pagination.next.disabled = data.page * data.per_page >= data.total;
      } catch (error) {
        console.error('Error loading recent sales:', error);
        document.getElementById('recent-sales-body').innerHTML = `
          <tr>
            <td colspan="6" class="px-6 py-4 text-center text-sm text-gray-500">Failed to load transactions. Please try again.</td>
          </tr>
        `;
      }
    }
  };

  // UI Helpers
  const uiHelpers = {
    showSellerSuggestions: (sellers) => {
      elements.sellerSuggestions.innerHTML = '';

      if (sellers.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'px-4 py-2 text-gray-500';
        noResults.textContent = 'No sellers found';
        elements.sellerSuggestions.appendChild(noResults);
      } else {
        sellers.forEach(seller => {
          const suggestion = document.createElement('div');
          suggestion.className = 'px-4 py-2 hover:bg-gray-100 cursor-pointer';
          suggestion.textContent = seller.name;
          suggestion.dataset.id = seller.id;

          suggestion.addEventListener('click', () => {
            elements.sellerFilter.value = seller.name;
            elements.sellerFilter.dataset.selectedId = seller.id;
            elements.sellerSuggestions.classList.add('hidden');
            dashboard.refreshAll();
          });

          elements.sellerSuggestions.appendChild(suggestion);
        });
      }

      elements.sellerSuggestions.classList.remove('hidden');
    },

    updateChartButtons: (activePeriod) => {
      Object.keys(elements.chartButtons).forEach(period => {
        elements.chartButtons[period].classList.toggle('bg-primary-100', period === activePeriod);
        elements.chartButtons[period].classList.toggle('text-primary-800', period === activePeriod);
        elements.chartButtons[period].classList.toggle('text-gray-500', period !== activePeriod);
        elements.chartButtons[period].classList.toggle('hover:bg-gray-50', period !== activePeriod);
      });
    },

    initializeDateRangePicker: () => {
      const defaultStartDate = new Date(Date.now() - config.defaultDateRange * 24 * 60 * 60 * 1000);
      const defaultEndDate = new Date();

      state.dateRangePicker = flatpickr("#date-range", {
        mode: "range",
        dateFormat: "Y-m-d",
        altInput: false,
        altFormat: "M j, Y",
        maxDate: "today",
        defaultDate: [defaultStartDate, defaultEndDate],
        onReady: function (selectedDates, dateStr, instance) {
          instance.setDate([defaultStartDate, defaultEndDate], false);
        },
        onClose: (selectedDates) => {
          if (selectedDates.length === 2) {
            dashboard.refreshAll();
          }
        }
      });
    }
  };

  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, '0');
    const day = `${date.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  };
  // Dashboard Controller
  const dashboard = {
    getQueryParams: () => {
      const sellerId = elements.sellerFilter?.dataset.selectedId || '';
      const selectedDates = state.dateRangePicker.selectedDates;

      let params = sellerId ? `?seller_id=${sellerId}` : '?';

      if (selectedDates && selectedDates.length === 2) {
        const startDate = formatDate(selectedDates[0]);
        const endDate = formatDate(selectedDates[1]);
        params += sellerId ? '&' : '';
        params += `start_date=${startDate}&end_date=${endDate}`;
      } else {
        const todayStr = formatDate(new Date());
        params += sellerId ? '&' : '';
        params += `start_date=${todayStr}&end_date=${todayStr}`;
      }

      console.log(params, ">>>>");
      return params;
    },

    refreshAll: async () => {
      utils.showLoader();
      try {
        const params = dashboard.getQueryParams();

        await Promise.all([
          dataFetchers.loadOverview(params),
          dataFetchers.loadSalesChart(`${params}&period=${state.chartPeriod}`),
          dataFetchers.loadTopProducts(params),
          dataFetchers.loadRecentSales(params, state.currentPage)
        ]);
      } catch (error) {
        console.error('Error refreshing dashboard:', error);
      } finally {
        utils.hideLoader();
      }
    },

    initializeEventListeners: () => {
      Object.keys(elements.chartButtons).forEach(period => {
        elements.chartButtons[period].addEventListener('click', () => {
          state.chartPeriod = period;
          uiHelpers.updateChartButtons(period);
          dashboard.refreshAll();
        });
      });

      elements.pagination.prev.addEventListener('click', () => {
        if (state.currentPage > 1) {
          state.currentPage--;
          dashboard.refreshAll();
        }
      });

      elements.pagination.next.addEventListener('click', () => {
        state.currentPage++;
        dashboard.refreshAll();
      });

      if (elements.sellerFilter) {
        elements.sellerFilter.addEventListener('change', dashboard.refreshAll);
      }
    },

    initialize: async () => {
      utils.showLoader();
      try {
        uiHelpers.initializeDateRangePicker();
        dashboard.initializeEventListeners();

        if (elements.sellerFilter) {
          await dataFetchers.loadSellers();
        }

        await dashboard.refreshAll();
      } catch (error) {
        console.error('Error initializing dashboard:', error);
      } finally {
        utils.hideLoader();
      }
    }
  };

  document.addEventListener('DOMContentLoaded', dashboard.initialize);
})();