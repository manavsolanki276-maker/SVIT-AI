/**
 * app/static/js/student/dashboard.js
 * Student ERP Portal Interactivity and Razorpay Checkout Engine.
 */

function openErpModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeErpModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

// Close modal when clicking on backdrop
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('erp-modal-backdrop')) {
        e.target.style.display = 'none';
        document.body.style.overflow = '';
    }
});

function openChatWithPrompt(query) {
    window.location.href = `/student/chat?q=${encodeURIComponent(query)}`;
}

/**
 * Trigger official Razorpay Checkout modal for online fee payment.
 */
async function triggerOnlinePayment(pendingAmount) {
    try {
        const createBtn = event?.target?.closest('button');
        if (createBtn) {
            createBtn.disabled = true;
            createBtn.innerHTML = '<span>Processing...</span>';
        }

        // 1. Create order on backend (Amount verified server-side)
        const orderRes = await fetch('/student/api/payment/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fee_type: 'tuition_fee' })
        });

        const orderData = await orderRes.json();
        if (createBtn) {
            createBtn.disabled = false;
            createBtn.innerHTML = `💳 Pay ₹${Number(pendingAmount).toLocaleString()}`;
        }

        if (!orderRes.ok || orderData.status === 'error') {
            alert(orderData.message || 'Unable to initiate payment.');
            return;
        }

        // 2. Open Razorpay Checkout modal
        if (typeof Razorpay === 'undefined') {
            alert('Payment gateway is loading. Please check your network connection and try again.');
            return;
        }

        const options = {
            key: orderData.key_id,
            amount: orderData.amount, // in paise
            currency: orderData.currency || 'INR',
            name: 'SVIT Vasad',
            description: 'Student Term Fee Payment',
            image: '/static/logo/svit%20logo%20u.png',
            order_id: orderData.order_id,
            handler: async function (response) {
                // 3. Cryptographic signature verification on backend
                try {
                    const verifyRes = await fetch('/student/api/payment/verify', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            payment_method: 'UPI / Online'
                        })
                    });

                    const verifyData = await verifyRes.json();
                    if (verifyRes.ok && verifyData.status === 'success') {
                        // Success modal / alert
                        const receiptNo = verifyData.receipt_number;
                        const msg = `✅ PAYMENT SUCCESSFUL!\n\n` +
                                    `Amount Paid: ₹${Number(verifyData.amount).toLocaleString()}\n` +
                                    `Transaction ID: ${verifyData.payment_id}\n` +
                                    `Receipt Number: ${receiptNo}\n\n` +
                                    `Click OK to download your official PDF fee receipt.`;
                        if (confirm(msg)) {
                            window.open(`/student/api/payment/receipt/${receiptNo}`, '_blank');
                        }
                        window.location.reload();
                    } else {
                        alert(verifyData.message || 'Payment verification failed.');
                    }
                } catch (verifyErr) {
                    console.error('Verification error:', verifyErr);
                    alert('Network error verifying payment. Please check with the Accounts section.');
                }
            },
            prefill: {
                name: orderData.student_name,
                email: orderData.student_email,
                contact: orderData.student_phone
            },
            theme: {
                color: '#8B5CF6'
            },
            modal: {
                ondismiss: async function () {
                    console.log('Payment modal dismissed');
                    try {
                        await fetch('/student/api/payment/failure', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                razorpay_order_id: orderData.order_id,
                                error_description: 'User dismissed checkout window.'
                            })
                        });
                    } catch (e) {}
                }
            }
        };

        const rzp = new Razorpay(options);
        rzp.on('payment.failed', async function (failedResponse) {
            console.warn('Payment failed:', failedResponse.error);
            try {
                await fetch('/student/api/payment/failure', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        razorpay_order_id: orderData.order_id,
                        error_description: failedResponse.error?.description || 'Payment failed'
                    })
                });
            } catch (e) {}
            alert(`❌ Payment failed: ${failedResponse.error?.description || 'Transaction could not be processed'}. You can try again.`);
        });
        rzp.open();

    } catch (err) {
        console.error('Payment checkout error:', err);
        alert('An unexpected error occurred while starting payment.');
    }
}
