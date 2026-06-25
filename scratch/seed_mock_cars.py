import asyncio
import uuid
from app.database import AsyncSessionLocal
from app.models.listing import Listing, PropertyType, City, ListingPurpose

MOCK_CARS_TO_SEED = [
    {
        "title": "Toyota Corolla 2018",
        "price": 11_500_000,
        "year": 2018,
        "colour": "Silver",
        "location": "Wuse 2, Abuja",
        "source_listing_id": "car_demo_1",
        "purpose": ListingPurpose.SALE
    },
    {
        "title": "Honda Accord 2017",
        "price": 12_800_000,
        "year": 2017,
        "colour": "Black",
        "location": "Garki, Abuja",
        "source_listing_id": "car_demo_2",
        "purpose": ListingPurpose.RENT
    },
    {
        "title": "Hyundai Elantra 2019",
        "price": 13_500_000,
        "year": 2019,
        "colour": "White",
        "location": "Maitama, Abuja",
        "source_listing_id": "car_demo_3",
        "purpose": ListingPurpose.SALE
    },
    {
        "title": "Kia Sportage 2016",
        "price": 14_200_000,
        "year": 2016,
        "colour": "Blue",
        "location": "Asokoro, Abuja",
        "source_listing_id": "car_demo_4",
        "purpose": ListingPurpose.RENT
    },
    {
        "title": "Lexus IS 250 2015",
        "price": 14_900_000,
        "year": 2015,
        "colour": "Red",
        "location": "Gwarinpa, Abuja",
        "source_listing_id": "car_demo_5",
        "purpose": ListingPurpose.SALE
    }
]

async def seed_cars():
    print("Connecting to database to seed mock cars...")
    async with AsyncSessionLocal() as session:
        for car_data in MOCK_CARS_TO_SEED:
            # Check if already exists
            existing = await session.run_sync(
                lambda s: s.query(Listing).filter_by(
                    source="realtorpal_cars_demo",
                    source_listing_id=car_data["source_listing_id"]
                ).first()
            )
            if existing:
                print(f"Car {car_data['title']} already exists, updating...")
                existing.title = car_data["title"]
                existing.price = car_data["price"]
                existing.bedrooms = car_data["year"]
                existing.description = f"Colour: {car_data['colour']}. Foreign used, excellent condition."
                existing.location = car_data["location"]
                existing.listing_purpose = car_data["purpose"]
            else:
                print(f"Creating car {car_data['title']}...")
                car = Listing(
                    id=uuid.uuid4(),
                    source="realtorpal_cars_demo",
                    source_listing_id=car_data["source_listing_id"],
                    title=car_data["title"],
                    description=f"Colour: {car_data['colour']}. Foreign used, excellent condition.",
                    price=car_data["price"],
                    currency="NGN",
                    property_type=PropertyType.CAR,
                    bedrooms=car_data["year"],  # Year of make
                    bathrooms=None,
                    toilets=None,
                    location=car_data["location"],
                    city=City.ABUJA,
                    state="FCT",
                    listing_purpose=car_data["purpose"],
                    agent_name="Premium Motors Ltd",
                    agent_phone="+2348012345678",
                    listing_url="https://wa.me/2348012345678",
                    image_url="https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=800&q=80"
                )
                session.add(car)
        await session.commit()
        print("Mock cars successfully seeded!")

if __name__ == "__main__":
    asyncio.run(seed_cars())
