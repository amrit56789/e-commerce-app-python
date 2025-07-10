function validateStep2(quill) {
    let isValid = true;

    isValid = validators.required(document.getElementById('title'), 'Title', 'title-error') && isValid;
    isValid = validators.required(document.getElementById('description'), 'Description', 'description-error') && isValid;

    const quillContent = quill.root.innerHTML;
    const productDetailsField = document.getElementById('product-details');
    productDetailsField.value = quillContent;
    isValid = validators.required(productDetailsField, 'Product Details', 'product-details-error') && isValid;

    isValid = validators.required(document.getElementById('price'), 'Price', 'price-error') && isValid;
    isValid = validators.required(document.getElementById('stock'), 'Stock', 'stock-error') && isValid;
    isValid = validators.required(document.getElementById('discount_price'), 'Discount Price', 'discount-error') && isValid;
    isValid = validators.required(document.getElementById('brand'), 'Brand', 'brand-error') && isValid;

    return isValid;
}


function validateStep3() {
    let isValid = true;
    
    // Check if at least one size block exists
    if (!validators.atLeastOneSize('size-container', 'Product')) {
      isValid = false;
    }
    
    // Validate each size block
    document.querySelectorAll('.size-block').forEach(block => {
      if (!validators.sizeSelection(block, 'Size')) {
        isValid = false;
      }
      
      if (!validators.colorQuantities(block, 'Color selection')) {
        isValid = false;
      }
    });
    
    return isValid;
  }

function validateStep4() {
    // Add your step 4 validation logic here
}
