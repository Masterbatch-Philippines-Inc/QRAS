function stripShepherdClass(event) {
  setTimeout(() => {
    const el = event.step?.el;
    if (!el) return;
    el.querySelectorAll('.shepherd-button').forEach(btn => {
      btn.classList.remove('shepherd-button');
    });
  }, 0);
}

function createTour(steps) {
  const tour = new Shepherd.Tour({
    useModalOverlay: true,
    defaultStepOptions: {
      cancelIcon: { enabled: true },
      scrollTo: { behavior: 'smooth', block: 'center' },
      modalOverlayOpeningRadius: 6,
      modalOverlayOpeningPadding: 4,
    },
  });

  tour.on('show', stripShepherdClass);

  steps.forEach((step, i) => {
    tour.addStep({
      ...step,
      buttons: step.buttons ?? buildButtons(tour, i, steps.length),
    });
  });

  return tour;
}

function buildButtons(tour, index, total) {
  const buttons = [];
  if (index > 0)
    buttons.push({ text: 'Back', classes: 'btn btn-md btn-ghost-secondary', action: () => tour.back() });
  if (index < total - 1)
    buttons.push({ text: 'Next', classes: 'btn btn-md btn-primary', action: () => tour.next() });
  else
    buttons.push({ text: 'Done', classes: 'btn btn-md btn-success', action: () => tour.complete() });
  return buttons;
}

function startTour(tourKey, tour) {
  tour.on('complete', () => localStorage.setItem(tourKey, '1'));
  tour.on('cancel',   () => localStorage.setItem(tourKey, '1'));
  tour.start();
}

function autoStartTour(tourKey, tour) {
  if (!localStorage.getItem(tourKey)) startTour(tourKey, tour);
}