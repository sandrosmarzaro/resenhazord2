from dataclasses import dataclass

USA = '🇺🇸 EUA'
ITALY = '🇮🇹 Itália'
UK = '🇬🇧 Reino Unido'
GERMANY = '🇩🇪 Alemanha'
CHINA = '🇨🇳 China'
FRANCE = '🇫🇷 França'
SK = '🇰🇷 Coreia do Sul'
JAPAN = '🇯🇵 Japão'


@dataclass(frozen=True)
class FipeBrand:
    name: str
    fipe_code: str
    emoji: str
    origin: str


FIPE_BRANDS: list[FipeBrand] = [
    FipeBrand(name='Acura', fipe_code='1', emoji='🚗', origin=USA),
    FipeBrand(name='Alfa Romeo', fipe_code='3', emoji='🏎️', origin=ITALY),
    FipeBrand(name='Aston Martin', fipe_code='189', emoji='🏎️', origin=UK),
    FipeBrand(name='Audi', fipe_code='6', emoji='🏎️', origin=GERMANY),
    FipeBrand(name='BMW', fipe_code='7', emoji='🏎️', origin=GERMANY),
    FipeBrand(name='BYD', fipe_code='238', emoji='🚗', origin=CHINA),
    FipeBrand(name='Cadillac', fipe_code='10', emoji='🚗', origin=USA),
    FipeBrand(name='CAOA Chery/Chery', fipe_code='161', emoji='🚗', origin=CHINA),
    FipeBrand(name='Chery', fipe_code='245', emoji='🚗', origin=CHINA),
    FipeBrand(name='Chrysler', fipe_code='12', emoji='🚗', origin=USA),
    FipeBrand(name='Citroën', fipe_code='13', emoji='🚗', origin=FRANCE),
    FipeBrand(name='Daewoo', fipe_code='15', emoji='🚗', origin=SK),
    FipeBrand(name='Daihatsu', fipe_code='16', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Dodge', fipe_code='17', emoji='🚗', origin=USA),
    FipeBrand(name='Ferrari', fipe_code='20', emoji='🏎️', origin=ITALY),
    FipeBrand(name='Fiat', fipe_code='21', emoji='🚗', origin=ITALY),
    FipeBrand(name='Ford', fipe_code='22', emoji='🚗', origin=USA),
    FipeBrand(name='Chevrolet', fipe_code='23', emoji='🚗', origin=USA),
    FipeBrand(name='Gurgel', fipe_code='24', emoji='🚗', origin='🇧🇷 Brasil'),
    FipeBrand(name='GWM', fipe_code='240', emoji='🚗', origin=CHINA),
    FipeBrand(name='Honda', fipe_code='25', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Hyundai', fipe_code='26', emoji='🚗', origin=SK),
    FipeBrand(name='Isuzu', fipe_code='27', emoji='🚙', origin=JAPAN),
    FipeBrand(name='IVECO', fipe_code='208', emoji='🚙', origin=ITALY),
    FipeBrand(name='JAC', fipe_code='177', emoji='🚗', origin=CHINA),
    FipeBrand(name='Jaguar', fipe_code='28', emoji='🏎️', origin=UK),
    FipeBrand(name='Jeep', fipe_code='29', emoji='🚙', origin=USA),
    FipeBrand(name='Kia', fipe_code='31', emoji='🚗', origin=SK),
    FipeBrand(name='Lada', fipe_code='32', emoji='🚗', origin='🇷🇺 Rússia'),
    FipeBrand(name='Lamborghini', fipe_code='171', emoji='🏎️', origin=ITALY),
    FipeBrand(name='Land Rover', fipe_code='33', emoji='🚙', origin=UK),
    FipeBrand(name='Lexus', fipe_code='34', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Lifan', fipe_code='168', emoji='🚗', origin=CHINA),
    FipeBrand(name='Lotus', fipe_code='35', emoji='🏎️', origin=UK),
    FipeBrand(name='Mahindra', fipe_code='140', emoji='🚙', origin='🇮🇳 Índia'),
    FipeBrand(name='Maserati', fipe_code='36', emoji='🏎️', origin=ITALY),
    FipeBrand(name='Mazda', fipe_code='38', emoji='🚗', origin=JAPAN),
    FipeBrand(name='McLaren', fipe_code='211', emoji='🏎️', origin=UK),
    FipeBrand(name='Mercedes-Benz', fipe_code='39', emoji='🚗', origin=GERMANY),
    FipeBrand(name='Mercury', fipe_code='40', emoji='🚗', origin=USA),
    FipeBrand(name='MG', fipe_code='167', emoji='🚗', origin=UK),
    FipeBrand(name='MINI', fipe_code='156', emoji='🚗', origin=UK),
    FipeBrand(name='Mitsubishi', fipe_code='41', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Nissan', fipe_code='43', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Peugeot', fipe_code='44', emoji='🚗', origin=FRANCE),
    FipeBrand(name='Plymouth', fipe_code='45', emoji='🚗', origin=USA),
    FipeBrand(name='Pontiac', fipe_code='46', emoji='🚗', origin=USA),
    FipeBrand(name='Porsche', fipe_code='47', emoji='🏎️', origin=GERMANY),
    FipeBrand(name='RAM', fipe_code='185', emoji='🚙', origin=USA),
    FipeBrand(name='Renault', fipe_code='48', emoji='🚗', origin=FRANCE),
    FipeBrand(name='Rolls-Royce', fipe_code='195', emoji='🚗', origin=UK),
    FipeBrand(name='Rover', fipe_code='49', emoji='🚗', origin=UK),
    FipeBrand(name='Saab', fipe_code='50', emoji='🚗', origin='🇸🇪 Suécia'),
    FipeBrand(name='Saturn', fipe_code='51', emoji='🚗', origin=USA),
    FipeBrand(name='SEAT', fipe_code='52', emoji='🚗', origin='🇪🇸 Espanha'),
    FipeBrand(name='Smart', fipe_code='157', emoji='🚗', origin=GERMANY),
    FipeBrand(name='SsangYong', fipe_code='125', emoji='🚙', origin=SK),
    FipeBrand(name='Subaru', fipe_code='54', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Suzuki', fipe_code='55', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Toyota', fipe_code='56', emoji='🚗', origin=JAPAN),
    FipeBrand(name='Troller', fipe_code='57', emoji='🚙', origin='🇧🇷 Brasil'),
    FipeBrand(name='Volvo', fipe_code='58', emoji='🚗', origin='🇸🇪 Suécia'),
    FipeBrand(name='Volkswagen', fipe_code='59', emoji='🚗', origin=GERMANY),
]
