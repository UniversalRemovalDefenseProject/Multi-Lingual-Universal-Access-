# Intake Interface Translations

The intake application is prepared for these priority locales:

- Spanish (`es`)
- French (`fr`)
- Arabic (`ar`)
- Haitian Creole (`ht`)
- Russian (`ru`)
- Hindi (`hi`)
- Punjabi (`pa`)
- Portuguese (`pt`)
- Chinese, Simplified (`zh_Hans` / `zh-hans`)

The `.po` files are intentionally ready for review by qualified translators.
Because intake instructions and legal disclaimers affect vulnerable users, do not
publish unreviewed machine translations as authoritative content. Populate the
catalogs from marked source strings before enabling non-English options in a
production release:

```powershell
python manage.py makemessages -l es -l fr -l ar -l ht -l ru -l hi -l pa -l pt -l zh_Hans
```

After translations are reviewed, compile them during deployment:

```powershell
python manage.py compilemessages
```

The application uses the submitted `language_preference` value to record the
interface language. Narrative answers remain exactly as submitted; staff can
place reviewed translations in the separate translated-response fields.
