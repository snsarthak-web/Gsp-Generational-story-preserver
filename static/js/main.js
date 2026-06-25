/**
 * GSP — Generational Story Preserver
 * Client-side utilities: voice input (Web Speech API), photo upload helpers, UI.
 */

var GSP = window.GSP || {};

// ---------------------------------------------------------------------------
// Voice input via Web Speech API
// ---------------------------------------------------------------------------
GSP.voice = (function() {
  var recognition = null;
  var activeField  = null;
  var recording    = false;

  function getRecognition() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;
    var r = new SpeechRecognition();
    r.continuous      = true;
    r.interimResults  = true;
    r.lang            = 'en-IN';
    return r;
  }

  function setStatus(msg) {
    var el = document.getElementById('voiceStatus');
    if (el) el.textContent = msg;
  }

  function setLabel(msg) {
    var el = document.getElementById('voiceLabel');
    if (el) el.textContent = msg;
  }

  function toggle(fieldId) {
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
      setStatus('Voice not supported in this browser. Try Chrome or Edge.');
      return;
    }

    var btn = document.querySelector('.voice-btn');

    if (recording) {
      // Stop
      if (recognition) recognition.stop();
      recording = false;
      activeField = null;
      if (btn) btn.classList.remove('recording');
      setLabel('Dictate');
      setStatus('');
      return;
    }

    // Start
    activeField = document.getElementById(fieldId);
    if (!activeField) return;

    recognition = getRecognition();
    if (!recognition) return;

    var existingText = activeField.value;
    var interim = '';

    recognition.onstart = function() {
      recording = true;
      if (btn) btn.classList.add('recording');
      setLabel('Stop');
      setStatus('Listening… speak now.');
    };

    recognition.onresult = function(event) {
      var final = '';
      interim = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        var t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      if (final) {
        existingText = (existingText + ' ' + final).trim();
        activeField.value = existingText;
      }
      setStatus(interim ? ('… ' + interim) : '');
    };

    recognition.onerror = function(e) {
      if (e.error !== 'aborted') setStatus('Error: ' + e.error);
      recording = false;
      if (btn) btn.classList.remove('recording');
      setLabel('Dictate');
    };

    recognition.onend = function() {
      if (recording) {
        // auto-restart on natural pause (continuous mode sometimes stops)
        try { recognition.start(); } catch(e) {}
      } else {
        setStatus('');
      }
    };

    try {
      recognition.start();
    } catch(e) {
      setStatus('Could not start microphone: ' + e.message);
    }
  }

  return { toggle: toggle };
})();


// ---------------------------------------------------------------------------
// Auto-dismiss flash messages (backup if template JS fails)
// ---------------------------------------------------------------------------
(function() {
  var fw = document.getElementById('flashWrap');
  if (fw) {
    setTimeout(function() {
      fw.style.transition = 'opacity 0.5s';
      fw.style.opacity = '0';
      setTimeout(function() { fw.remove(); }, 500);
    }, 3500);
  }
})();
