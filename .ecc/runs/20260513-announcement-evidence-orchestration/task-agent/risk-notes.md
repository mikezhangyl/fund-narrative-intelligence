# Risk Notes

- CNINFO remains opt-in; default report generation does not call the provider.
- Announcement evidence still classifies metadata only and does not parse source PDFs.
- Opting in with non-A-share holdings produces invalid stock-code degradation events and no generated announcement evidence.
- Generated announcement evidence can change evidence density but still relies on fixture-backed signals until a real signal-generation path exists.
