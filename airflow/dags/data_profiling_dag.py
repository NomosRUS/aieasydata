import os
import requests
from datetime import datetime

from airflow.decorators import dag, task

DATA_LANDING_ZONE = os.environ.get("DATA_LANDING_ZONE", "/opt/airflow/data_landing_zone")

@dag(
    dag_id='data_profiling_pipeline',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@daily',
    catchup=False,
    tags=['data-engineering', 'profiling'],
)
def data_profiling_dag():
    """
    ### Data Profiling DAG
    This DAG scans a directory, profiles the files, and saves the metadata to Postgres.
    """

    @task
    def run_profiling():
        """
        Scans the data landing zone, profiles each source, and saves the metadata to the database.
        """
        print(f"Starting data profiling pipeline for path: {DATA_LANDING_ZONE}")

        # Add backend to path to import our modules
        import sys
        sys.path.append('/opt/airflow/backend')

        from app.profiler import profile_source, classify_table
        from app.database import get_db, upsert_data_profile

        db = next(get_db())
        sources_found = 0
        try:
            for item in os.listdir(DATA_LANDING_ZONE):
                source_path = os.path.join(DATA_LANDING_ZONE, item)
                if os.path.isdir(source_path):
                    print(f"Profiling source: {source_path}")
                    
                    # Profile the source directory
                    profile_result = profile_source(source_path)
                    
                    if profile_result.get('error'):
                        print(f"❌ Error profiling {source_path}: {profile_result['error']}")
                        # Still save the error state to the DB
                        upsert_data_profile(db, profile_result)
                        continue
                    
                    # Classify the table
                    profile_result['kind'] = classify_table(profile_result)
                    
                    # Save to DB
                    upsert_data_profile(db, profile_result)
                    sources_found += 1
                    print(f"✅ Successfully profiled {source_path}")
            
            db.commit()
            print(f"✅ Profiling finished. Processed {sources_found} sources.")
            return f"Profiling finished. Processed {sources_found} sources."

        except Exception as e:
            print(f"❌ A critical error occurred: {e}")
            db.rollback()
            # Re-raise the exception to make the task fail
            raise
        finally:
            db.close()

    run_profiling()

data_profiling_dag_instance = data_profiling_dag()
