// ── AOS Init ──
    AOS.init({
      duration: 700,
      once: true,
      easing: 'ease-out-cubic',
      offset: 60,
    });

    // ── Progress bar ──
    window.addEventListener('scroll', () => {
      const scrollTop = document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const progress = (scrollTop / scrollHeight) * 100;
      document.getElementById('progress-bar').style.width = progress + '%';
    });

    // ── Navbar scroll ──
    window.addEventListener('scroll', () => {
      const nav = document.getElementById('navbar');
      if (window.scrollY > 20) {
        nav.classList.add('scrolled');
      } else {
        nav.classList.remove('scrolled');
      }
    });

    // ── Hamburger ──
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobile-menu');
    let menuOpen = false;

    hamburger.addEventListener('click', () => {
      menuOpen = !menuOpen;
      if (menuOpen) {
        mobileMenu.classList.add('open');
        const lines = hamburger.querySelectorAll('.ham-line');
        lines[0].style.transform = 'translateY(8px) rotate(45deg)';
        lines[1].style.opacity = '0';
        lines[2].style.transform = 'translateY(-8px) rotate(-45deg)';
        lines[2].style.width = '20px';
      } else {
        closeMobileMenu();
      }
    });

    function closeMobileMenu() {
      menuOpen = false;
      mobileMenu.classList.remove('open');
      const lines = hamburger.querySelectorAll('.ham-line');
      lines[0].style.transform = '';
      lines[1].style.opacity = '1';
      lines[2].style.transform = '';
      lines[2].style.width = '12px';
    }

    // Close menu on outside click
    document.addEventListener('click', (e) => {
      if (menuOpen && !hamburger.contains(e.target) && !mobileMenu.contains(e.target)) {
        closeMobileMenu();
      }
    });

    // ── Form submit ──
    async function handleFormSubmit(e) {
      e.preventDefault();
      const form = e.target;
      const btn = form.querySelector('button[type="submit"]');
      const btnText = document.getElementById('form-btn-text');
      
      btnText.textContent = 'Sending...';
      btn.disabled = true;

      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());
      
      if (data.country_code && data.mobile_number) {
          data.mobile = data.country_code + data.mobile_number.trim();
          delete data.country_code;
          delete data.mobile_number;
      } else {
          data.mobile = "";
      }

      try {
        const response = await fetch('/api/contact', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (result.success) {
          document.getElementById('contact-form').style.display = 'none';
          document.getElementById('form-success').classList.remove('hidden');
        } else {
          alert('Error: ' + result.message);
          btnText.textContent = 'Book My Free Consultation';
          btn.disabled = false;
        }
      } catch (error) {
        console.error('Error submitting form:', error);
        alert('An error occurred. Please try again.');
        btnText.textContent = 'Book My Free Consultation';
        btn.disabled = false;
      }
    }

    // ── Smooth scroll for nav links ──
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          e.preventDefault();
          const offset = 80;
          const targetPos = target.getBoundingClientRect().top + window.scrollY - offset;
          window.scrollTo({ top: targetPos, behavior: 'smooth' });
        }
      });
    });

    // ── Close Success Message ──
    const closeSuccessBtn = document.getElementById('close-success-btn');
    if (closeSuccessBtn) {
      closeSuccessBtn.addEventListener('click', () => {
        document.getElementById('form-success').classList.add('hidden');
        const form = document.getElementById('contact-form');
        form.reset();
        form.style.display = 'block';
        
        const btnText = document.getElementById('form-btn-text');
        const btn = form.querySelector('button[type="submit"]');
        btnText.textContent = 'Book My Free Consultation';
        btn.disabled = false;
      });
    }