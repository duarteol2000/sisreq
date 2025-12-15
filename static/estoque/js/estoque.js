// JS específico do módulo de estoque
(function(){
  function attachDecimalKeyguard(input, allowSign){
    input.addEventListener('keydown', function(e){
      const k = e.key;
      if (k === 'Backspace' || k === 'Delete' || k === 'Tab' || k === 'Enter' || k === 'Escape' ||
          k === 'Home' || k === 'End' || k === 'ArrowLeft' || k === 'ArrowRight') { e.stopImmediatePropagation(); return; }
      if (/^[0-9]$/.test(k)) { e.stopImmediatePropagation(); return; }
      if (allowSign && k === '-' && input.selectionStart === 0 && !input.value.includes('-')) { e.stopImmediatePropagation(); return; }
      if (k === ',' || k === '.') { e.stopImmediatePropagation(); return; }
      e.stopImmediatePropagation();
      e.preventDefault();
    }, true);
  }
  function attachDecimalMask(input, maxDecimals, allowSign){
    attachDecimalKeyguard(input, allowSign);
    function sanitize(val){
      if(!val) return '';
      let s = String(val).replace(/\s+/g,'');
      s = s.replace(/\./g, ',');
      let sign = '';
      if(allowSign && s[0] === '-') { sign = '-'; s = s.slice(1); }
      s = s.replace(/[^0-9,]/g,'');
      const parts = s.split(',');
      if(parts.length > 1){
        let int = parts.shift()||'';
        let dec = parts.join('');
        if(typeof maxDecimals === 'number') dec = dec.slice(0, maxDecimals);
        s = int + (dec.length ? ','+dec : '');
      }
      return sign + s;
    }
    input.addEventListener('input', ()=>{
      const cur = input.value; const san = sanitize(cur);
      if(cur !== san) input.value = san;
    });
  }

  // Variante sem keyguard: não bloqueia teclas, apenas saneia e limita casas
  function attachDecimalMaskNoKeyguard(input, maxDecimals){
    function sanitize(val){
      if(!val) return '';
      let s = String(val).replace(/\s+/g,'');
      s = s.replace(/\./g, ',');
      // mantém apenas dígitos, vírgula e sinal opcional no início (não usaremos sinal aqui)
      s = s.replace(/[^0-9,\-]/g,'');
      const parts = s.split(',');
      if(parts.length > 1){
        let int = parts.shift()||'';
        let dec = parts.join('');
        if(typeof maxDecimals === 'number') dec = dec.slice(0, maxDecimals);
        s = int + (dec.length ? ','+dec : '');
      }
      return s;
    }
    input.addEventListener('input', ()=>{
      const cur = input.value; const san = sanitize(cur);
      if(cur !== san) input.value = san;
    });
  }
  function attachIntMask(input){
    input.addEventListener('input', ()=>{
      const cur = input.value; const san = String(cur).replace(/\D+/g,'');
      if(cur !== san) input.value = san;
    });
  }
  function attachDocMask(input){
    input.addEventListener('input', ()=>{
      let v = (input.value||'').replace(/\D+/g,'').slice(0,14);
      if(v.length <= 11){
        v = v.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
      }else{
        v = v.replace(/(\d{2})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1/$2').replace(/(\d{4})(\d{1,2})$/, '$1-$2');
      }
      input.value = v;
    });
  }
  function attachPhoneMask(input){
    input.addEventListener('input', ()=>{
      let v = (input.value||'').replace(/\D+/g,'').slice(0,11);
      if(v.length <= 10){
        v = v.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{4})(\d)/, '$1-$2');
      } else {
        v = v.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
      }
      input.value = v;
    });
  }
  function attachCepMask(input){
    input.addEventListener('input', ()=>{
      let v = (input.value||'').replace(/\D+/g,'').slice(0,8);
      v = v.replace(/(\d{5})(\d)/, '$1-$2');
      input.value = v;
    });
  }

  document.querySelectorAll('input.js-decimal-2').forEach(el=> {
    try{ el.type = 'text'; el.removeAttribute('pattern'); el.removeAttribute('step'); el.setAttribute('inputmode','decimal'); }catch(_){ }
    // Usa máscara sem keyguard para máxima compatibilidade com vírgula/ponto
    attachDecimalMaskNoKeyguard(el, 2);
  });
  document.querySelectorAll('input.js-decimal-6').forEach(el=> attachDecimalMask(el, 6, true));
  document.querySelectorAll('input.js-int').forEach(el=> attachIntMask(el));
  document.querySelectorAll('input.js-doc').forEach(el=> attachDocMask(el));
  document.querySelectorAll('input.js-phone').forEach(el=> attachPhoneMask(el));
  document.querySelectorAll('input.js-cep').forEach(el=> attachCepMask(el));
})();

// ===== Login: carregar secretarias por código IBGE em tempo real =====
document.addEventListener('DOMContentLoaded', function(){
  const form = document.getElementById('login-form');
  if (!form) return;

  const codigoInput = document.getElementById('id_codigo_ibge');
  const secretariaSelect = document.getElementById('id_secretaria');
  const url = form.dataset.secretariasUrl;

  if (!codigoInput || !secretariaSelect || !url) return;

  function atualizarSecretarias(){
    const codigo = (codigoInput.value || '').trim();
    secretariaSelect.innerHTML = '';

    if (!codigo){
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'Informe o código IBGE primeiro';
      secretariaSelect.appendChild(opt);
      secretariaSelect.disabled = true;
      return;
    }

    secretariaSelect.disabled = true;
    const loadingOpt = document.createElement('option');
    loadingOpt.value = '';
    loadingOpt.textContent = 'Carregando secretarias...';
    secretariaSelect.appendChild(loadingOpt);

    fetch(url + '?codigo_ibge=' + encodeURIComponent(codigo))
      .then(resp => resp.ok ? resp.json() : Promise.reject())
      .then(data => {
        secretariaSelect.innerHTML = '';
        const optDefault = document.createElement('option');
        optDefault.value = '';
        optDefault.textContent = 'Selecione a secretaria';
        secretariaSelect.appendChild(optDefault);

        (data.secretarias || []).forEach(item => {
          const opt = document.createElement('option');
          opt.value = item.id;
          opt.textContent = item.nome + (item.sigla ? ' (' + item.sigla + ')' : '');
          secretariaSelect.appendChild(opt);
        });

        secretariaSelect.disabled = false;
      })
      .catch(() => {
        secretariaSelect.innerHTML = '';
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Erro ao carregar secretarias';
        secretariaSelect.appendChild(opt);
        secretariaSelect.disabled = true;
      });
  }

  codigoInput.addEventListener('change', atualizarSecretarias);
  codigoInput.addEventListener('blur', atualizarSecretarias);
});
