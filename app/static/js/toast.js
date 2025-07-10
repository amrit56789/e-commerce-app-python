
function showToast(message, type = 'success', duration = 3000) {
    const toastContainer = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.classList.add('p-3', 'text-sm' ,'rounded-md', 'shadow-lg', 'text-white', 'w-80', 'max-w-xs', 'transition-all', 'duration-300');
    if (type === 'success') {
      toast.classList.add('bg-green-600');
    } else if (type === 'error') {
      toast.classList.add('bg-red-600');
    } else if (type === 'info') {
      toast.classList.add('bg-blue-600');
    } else {
      toast.classList.add('bg-yellow-600');
    }
  
    toast.innerText = message;
  
    toastContainer.appendChild(toast);
  
    setTimeout(() => {
      toast.classList.add('opacity-0');
      toast.classList.add('translate-x-full');
      setTimeout(() => {
        toast.remove();
      }, 300);
    }, duration);
  }
  